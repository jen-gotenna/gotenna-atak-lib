import pytest

from atak_lib import catalog, registry
from atak_lib.session.stub_driver import StubWebDriver


def test_catalog_registers_onboarding_command():
    assert "ui.verify_onboarding_screen" in registry.available()
    spec = registry.get("ui.verify_onboarding_screen")
    assert spec.layer == "ui"
    assert spec.summary


def test_run_via_registry_stub():
    result = catalog.run("ui.verify_onboarding_screen", StubWebDriver(), stub=True)
    assert result.passed


def test_unknown_command_raises_with_hint():
    with pytest.raises(KeyError) as exc:
        registry.get("ui.does_not_exist")
    assert "Available" in str(exc.value)


def test_duplicate_registration_raises():
    registry.register("tmp.dummy", lambda d, *, stub=False: None)
    with pytest.raises(ValueError):
        registry.register("tmp.dummy", lambda d, *, stub=False: None)


def test_command_callable_is_unchanged_and_tagged():
    from atak_lib.ui.verify_onboarding_screen import verify_onboarding_screen
    assert verify_onboarding_screen.command_name == "ui.verify_onboarding_screen"
    # still directly callable
    assert verify_onboarding_screen(StubWebDriver(), stub=True).passed
