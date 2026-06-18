"""The public API surface is intentional and stable -- guard it.

Everything in ``atak_lib.__all__`` must import cleanly; importing ``atak_lib`` must
not pull in Appium (it's a lazy/optional dep); and engine internals must stay off
the surface.
"""
import importlib
import sys

import atak_lib

_EXPECTED = {
    "catalog", "runtime",
    "SessionManager", "DeviceSpec",
    "ScreenVerificationResult", "CommandSpec",
    "load_command_spec", "load_command_spec_by_name", "register_spec_root",
    "verify_screen",
    "verify_onboarding_screen", "verify_device_details_screen",
    "verify_set_as_relay_dialog",
}


def test_all_names_are_importable():
    for name in atak_lib.__all__:
        assert hasattr(atak_lib, name), f"{name} in __all__ but not importable"


def test_surface_matches_expected():
    assert set(atak_lib.__all__) == _EXPECTED
    assert len(atak_lib.__all__) == len(set(atak_lib.__all__))   # no dupes


def test_verify_screen_is_callable():
    assert callable(atak_lib.verify_screen)


def test_importing_atak_lib_does_not_import_appium():
    # Appium must stay lazy/optional: a plain import must not pull it in.
    for mod in [m for m in sys.modules if m == "appium" or m.startswith("appium.")]:
        del sys.modules[mod]
    importlib.reload(atak_lib)
    assert "appium" not in sys.modules


def test_engine_internals_stay_private():
    for name in ("ScreenCommand", "registry", "stub_driver", "capabilities"):
        assert name not in atak_lib.__all__
