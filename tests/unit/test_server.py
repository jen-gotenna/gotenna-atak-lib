"""Service boundary: wire contract + session lifecycle, exercised socket-free.

``ApiApp.dispatch`` is the testable core (the HTTP handler is a thin adapter). A
factory is injected so tests can inspect the driver the session drove.
"""
from atak_lib.server.app import SCHEMA_VERSION, ApiApp, make_server
from atak_lib.session.stub_driver import StubWebDriver

LOGIN = ("id", "com.gotenna.atak:id/loginButton")


def _app_with(driver):
    return ApiApp(driver_factory=lambda spec: (driver, None))


def _open(app, **body):
    status, b = app.dispatch("POST", "/api/session", {}, {"stub": True, **body})
    assert status == 200
    return b["sessionId"]


# ---- selectors endpoint -----------------------------------------------------

def test_get_selectors_returns_definitions():
    status, body = ApiApp().dispatch("GET", "/api/selectors/ui.onboarding", {}, {})
    assert status == 200 and body["schemaVersion"] == SCHEMA_VERSION
    assert body["selectors"]["login_button"] == {
        "by": "id", "value": "com.gotenna.atak:id/loginButton", "status": "CONFIRMED"}


def test_get_selectors_unknown_screen_404():
    status, body = ApiApp().dispatch("GET", "/api/selectors/ui.nope", {}, {})
    assert status == 404 and "error" in body


# ---- session lifecycle + action/query --------------------------------------

def test_session_open_action_query_close():
    drv = StubWebDriver(present_all=True)
    app = _app_with(drv)
    sid = _open(app)

    st, b = app.dispatch("POST", "/api/action", {}, {
        "sessionId": sid, "screen": "ui.onboarding",
        "element": "login_button", "action": "tap"})
    assert st == 200 and b["ok"] is True
    assert drv.taps == [LOGIN]

    st, b = app.dispatch("POST", "/api/query", {}, {
        "sessionId": sid, "screen": "ui.onboarding",
        "element": "login_button", "query": "is_present"})
    assert st == 200 and b["value"] is True

    st, b = app.dispatch("DELETE", f"/api/session/{sid}", {}, {})
    assert st == 200 and b["closed"] is True

    # the session id is now unknown
    st, b = app.dispatch("POST", "/api/action", {}, {
        "sessionId": sid, "screen": "ui.onboarding",
        "element": "login_button", "action": "tap"})
    assert st == 404


def test_type_action_carries_text():
    drv = StubWebDriver(present_all=True)
    app = _app_with(drv)
    sid = _open(app)
    app.dispatch("POST", "/api/action", {}, {
        "sessionId": sid, "screen": "ui.onboarding", "element": "login_button",
        "action": "type", "args": {"text": "hello"}})
    assert drv.typed[-1] == (*LOGIN, "hello")


def test_close_called_on_session_close():
    closed = []
    app = ApiApp(driver_factory=lambda spec: (StubWebDriver(), lambda: closed.append(True)))
    sid = _open(app)
    app.dispatch("DELETE", f"/api/session/{sid}", {}, {})
    assert closed == [True]


def test_unknown_session_is_404():
    st, b = ApiApp().dispatch("POST", "/api/query", {}, {
        "sessionId": "nope", "screen": "ui.onboarding",
        "element": "login_button", "query": "is_present"})
    assert st == 404


def test_missing_field_is_400():
    app = _app_with(StubWebDriver(present_all=True))
    sid = _open(app)
    st, b = app.dispatch("POST", "/api/action", {}, {"sessionId": sid, "screen": "ui.onboarding"})
    assert st == 400 and "element" in b["error"]


def test_default_factory_rejects_real_session_without_injection():
    # No stub flag + default factory -> 400 (real sessions need an injected factory).
    st, b = ApiApp().dispatch("POST", "/api/session", {}, {})
    assert st == 400


def test_unknown_action_400():
    app = _app_with(StubWebDriver(present_all=True))
    sid = _open(app)
    st, b = app.dispatch("POST", "/api/action", {}, {
        "sessionId": sid, "screen": "ui.onboarding",
        "element": "login_button", "action": "frobnicate"})
    assert st == 400


# ---- wire contract ----------------------------------------------------------

def test_every_response_carries_schema_version():
    app = ApiApp()
    responses = [
        app.dispatch("GET", "/api/selectors/ui.onboarding", {}, {}),
        app.dispatch("GET", "/api/selectors/ui.nope", {}, {}),       # 404
        app.dispatch("POST", "/api/nope", {}, {}),                   # no route
    ]
    assert all(body["schemaVersion"] == SCHEMA_VERSION for _, body in responses)


# ---- HTTP wiring (bind only, no serve) --------------------------------------

def test_make_server_binds_a_port():
    srv = make_server(host="127.0.0.1", port=0)   # ephemeral port
    try:
        assert srv.server_address[1] > 0
    finally:
        srv.server_close()
