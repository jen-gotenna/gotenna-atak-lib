"""Language-agnostic HTTP service boundary (QA-3933 Phase 4).

The non-Python front door: exposes the selector catalog + the ``Screen`` driver over
HTTP so consumers like QWIK reach the one engine without reimplementing it. Optional
(`[server]` extra; stdlib-only today). Console entry point: ``atak-lib-server``.
"""
from atak_lib.server.app import SCHEMA_VERSION, ApiApp, main, make_server

__all__ = ["ApiApp", "make_server", "main", "SCHEMA_VERSION"]
