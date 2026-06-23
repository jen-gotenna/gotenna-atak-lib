"""atak_lib -- env-agnostic ATAK UI driver + command library.

This module IS the public API. Anything not re-exported here -- e.g. ``registry``,
the ``ui.base`` engine internals (``ScreenCommand``), ``session.capabilities``,
``session.stub_driver`` -- is private and may change without a major-version bump.

Importing ``atak_lib`` reads no environment variables and does NOT import Appium
(Appium is imported lazily only when a real session connects), so it is safe to
import in any context, hardware or not.

Quickstart -- drive + assert (the library reports facts; you own the assertions)::

    from atak_lib import SessionManager, DeviceSpec, Screen

    with SessionManager([DeviceSpec(udid="...")], stub=False) as s:
        screen = Screen("ui.onboarding", s.driver)
        screen.tap("login_button")
        assert screen.is_present("terms_of_service_checkbox")   # your expectation

The legacy ``verify_screen`` / ``verify_*`` path (the library-asserts model) is
deprecated; migrate to ``Screen`` + your own assertions (see
``docs/migration-verify-to-screen.md``). Non-Python consumers use the HTTP service
boundary (``atak_lib.server`` / the ``atak-lib-server`` console script).
"""
from atak_lib import catalog, runtime
from atak_lib.session.session_manager import DeviceSpec, SessionManager
from atak_lib.spec import (
    CommandSpec,
    load_command_spec,
    load_command_spec_by_name,
    register_spec_root,
)
from atak_lib.selectors import (
    Selector,
    SelectorCatalog,
    load_catalog,
    register_catalog_root,
)
from atak_lib.ui.base import ScreenVerificationResult
from atak_lib.ui.screen import Screen
from atak_lib.ui.verify import verify_screen
from atak_lib.ui.verify_device_details_screen import verify_device_details_screen
from atak_lib.ui.verify_onboarding_screen import verify_onboarding_screen
from atak_lib.ui.verify_set_as_relay_dialog import verify_set_as_relay_dialog

__all__ = [
    # command catalog (run / available / all_specs / get) + env-free runtime helpers
    "catalog",
    "runtime",
    # sessions & devices
    "SessionManager",
    "DeviceSpec",
    # UI driver: manipulation + state facade, and the selector catalog
    "Screen",
    "Selector",
    "SelectorCatalog",
    "load_catalog",
    "register_catalog_root",
    # result & spec types (the typed surface)
    "ScreenVerificationResult",
    "CommandSpec",
    # spec loading / consumer extension
    "load_command_spec",
    "load_command_spec_by_name",
    "register_spec_root",
    # screen verification
    "verify_screen",
    "verify_onboarding_screen",
    "verify_device_details_screen",
    "verify_set_as_relay_dialog",
]
