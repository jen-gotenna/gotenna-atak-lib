"""HTTP service boundary -- the non-Python front door (QA-3933 Phase 4).

Exposes the selector catalog + the ``Screen`` driver over HTTP so non-Python consumers
(QWIK/TS, other apps) reach the ONE engine without reimplementing it or holding their
own selectors. Session lifecycle is **open/close**: a consumer opens a session once (a
device, or a stub), drives many action/query calls against the reusable session id,
then closes it.

The server reads no env (consistent with the library): the client states the target
(`{"stub": true}` or a device) on ``POST /api/session``. Real-device sessions require
an injected ``driver_factory``; the stub path needs nothing.

Stdlib only (``http.server``). All requests/responses are JSON; every response carries
``schemaVersion``. Endpoints:

  GET    /api/selectors/<screen>[?version=]              -> selector definitions
  POST   /api/session   {stub:true | device:{...}}       -> {sessionId}
  DELETE /api/session/<id>                               -> {closed:true}
  POST   /api/action    {sessionId, screen, element, action, args?, version?}
  POST   /api/query     {sessionId, screen, element, query, version?}

``action`` in {tap, type, wait_for, scroll_into_view}; ``query`` in
{is_present, is_enabled, get_text}. The wire schema is a versioned contract
(``SCHEMA_VERSION``) pinned by tests.
"""
from __future__ import annotations

import argparse
import json
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from atak_lib.selectors import load_catalog
from atak_lib.ui.screen import Screen

SCHEMA_VERSION = "1"

# (driver, closer|None) -- closer is called on session close (e.g. to quit Appium).
DriverFactory = Callable[[Dict[str, Any]], Tuple[Any, Optional[Callable[[], None]]]]


def _default_driver_factory(spec: Dict[str, Any]):
    """Stub-only default. Real-device sessions require an injected factory so the
    library makes no assumptions about how a real Appium session is built."""
    if spec.get("stub"):
        from atak_lib.session.stub_driver import StubWebDriver
        return StubWebDriver(), None
    raise ValueError(
        'real-device sessions require an injected driver_factory; construct '
        'ApiApp(driver_factory=...) or POST {"stub": true}')


def _field(body: Dict[str, Any], name: str) -> Any:
    if name not in body:
        raise ValueError(f"missing field: {name}")
    return body[name]


class ApiApp:
    """Socket-free request core. ``dispatch`` is the testable unit; the HTTP server
    is a thin adapter over it."""

    def __init__(self, driver_factory: DriverFactory = _default_driver_factory):
        self._factory = driver_factory
        self._sessions: Dict[str, Tuple[Any, Optional[Callable[[], None]]]] = {}

    def dispatch(self, method: str, path: str,
                 query: Optional[Dict] = None,
                 body: Optional[Dict] = None) -> Tuple[int, Dict[str, Any]]:
        query = query or {}
        body = body or {}
        parts = [p for p in path.strip("/").split("/") if p]
        try:
            if method == "GET" and parts[:2] == ["api", "selectors"]:
                return self._get_selectors("/".join(parts[2:]), query)
            if method == "POST" and parts == ["api", "session"]:
                return self._open_session(body)
            if method == "DELETE" and parts[:2] == ["api", "session"] and len(parts) == 3:
                return self._close_session(parts[2])
            if method == "POST" and parts == ["api", "action"]:
                return self._action(body)
            if method == "POST" and parts == ["api", "query"]:
                return self._query(body)
        except FileNotFoundError as e:
            return self._err(404, str(e))
        except KeyError as e:
            return self._err(404, str(e))
        except ValueError as e:
            return self._err(400, str(e))
        return self._err(404, f"no route: {method} /{'/'.join(parts)}")

    # --- routes ---
    def _get_selectors(self, screen: str, query: Dict):
        if not screen:
            raise ValueError("screen required")
        version = (query.get("version") or [None])[0]
        cat = load_catalog(screen)              # FileNotFoundError -> 404
        selectors = {}
        for name, sel in cat.selectors.items():
            by, value = sel.for_version(version).as_tuple()
            selectors[name] = {"by": by, "value": value, "status": sel.status}
        return self._ok({"screen": cat.screen, "version": version,
                         "selectors": selectors})

    def _open_session(self, body: Dict):
        driver, closer = self._factory(body)    # ValueError -> 400 (e.g. real w/o factory)
        sid = uuid.uuid4().hex
        self._sessions[sid] = (driver, closer)
        return self._ok({"sessionId": sid})

    def _close_session(self, sid: str):
        entry = self._sessions.pop(sid, None)
        if entry is None:
            raise KeyError(f"unknown session: {sid}")
        _, closer = entry
        if closer:
            closer()
        return self._ok({"closed": True})

    def _screen_for(self, body: Dict) -> Screen:
        sid = _field(body, "sessionId")
        if sid not in self._sessions:
            raise KeyError(f"unknown session: {sid}")
        driver, _ = self._sessions[sid]
        return Screen(_field(body, "screen"), driver, version=body.get("version"))

    def _action(self, body: Dict):
        s = self._screen_for(body)
        element = _field(body, "element")
        action = _field(body, "action")
        args = body.get("args") or {}
        if action == "tap":
            s.tap(element)
            return self._ok({"action": action, "element": element, "ok": True})
        if action == "type":
            s.type(element, args.get("text", ""), clear=args.get("clear", True))
            return self._ok({"action": action, "element": element, "ok": True})
        if action == "wait_for":
            found = s.wait_for(element, timeout=args.get("timeout"))
            return self._ok({"action": action, "element": element,
                             "ok": True, "found": found})
        if action == "scroll_into_view":
            found = s.scroll_into_view(element)
            return self._ok({"action": action, "element": element,
                             "ok": True, "found": found})
        raise ValueError(f"unknown action: {action!r}")

    def _query(self, body: Dict):
        s = self._screen_for(body)
        element = _field(body, "element")
        q = _field(body, "query")
        if q == "is_present":
            value: Any = s.is_present(element)
        elif q == "is_enabled":
            value = s.is_enabled(element)
        elif q == "get_text":
            value = s.get_text(element)
        else:
            raise ValueError(f"unknown query: {q!r}")
        return self._ok({"query": q, "element": element, "value": value})

    @staticmethod
    def _ok(d: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        return 200, {"schemaVersion": SCHEMA_VERSION, **d}

    @staticmethod
    def _err(status: int, msg: str) -> Tuple[int, Dict[str, Any]]:
        return status, {"schemaVersion": SCHEMA_VERSION, "error": msg}


def _make_handler(app: ApiApp):
    class _Handler(BaseHTTPRequestHandler):
        def _run(self, method: str):
            parsed = urlparse(self.path)
            body: Dict[str, Any] = {}
            length = int(self.headers.get("Content-Length") or 0)
            if length:
                raw = self.rfile.read(length)
                try:
                    body = json.loads(raw or b"{}")
                except json.JSONDecodeError:
                    return self._send(400, {"schemaVersion": SCHEMA_VERSION,
                                            "error": "invalid JSON body"})
            status, payload = app.dispatch(method, parsed.path,
                                           parse_qs(parsed.query), body)
            self._send(status, payload)

        def _send(self, status: int, payload: Dict[str, Any]):
            data = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self._run("GET")

        def do_POST(self):
            self._run("POST")

        def do_DELETE(self):
            self._run("DELETE")

        def log_message(self, *args):
            pass   # quiet by default

    return _Handler


def make_server(host: str = "127.0.0.1", port: int = 8770,
                app: Optional[ApiApp] = None) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), _make_handler(app or ApiApp()))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="atak-lib-server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8770)
    args = parser.parse_args(argv)
    server = make_server(args.host, args.port)
    print(f"atak-lib-server on http://{args.host}:{args.port} "
          f"(schema v{SCHEMA_VERSION})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
