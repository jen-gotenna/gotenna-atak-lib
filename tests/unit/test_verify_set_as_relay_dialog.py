from atak_lib.session.stub_driver import StubWebDriver
from atak_lib.ui.locators import CONFIRMED, BY_XPATH
from atak_lib.ui.verify_set_as_relay_dialog import (
    SET_AS_RELAY_LOCATORS,
    SPEC,
    TARGET_PLUGIN_VERSION,
    TESTRAIL_CASE_ID,
    verify_set_as_relay_dialog,
)

UIA = "-android uiautomator"
EXPECTED_COMPONENTS = {
    "dialog_title", "dialog_body", "cancel_button", "set_as_relay_button",
}


def _by_name():
    return {l.name: l for l in SET_AS_RELAY_LOCATORS}


def test_targets_plugin_3_0_and_case_c149725():
    assert TARGET_PLUGIN_VERSION == "3.0"
    assert TESTRAIL_CASE_ID == "C149725"


def test_four_confirmed_xpath_free_components():
    assert len(SET_AS_RELAY_LOCATORS) == 4
    assert {l.name for l in SET_AS_RELAY_LOCATORS} == EXPECTED_COMPONENTS
    assert all(l.status == CONFIRMED for l in SET_AS_RELAY_LOCATORS)
    assert all(l.by != BY_XPATH for l in SET_AS_RELAY_LOCATORS)   # xpath-free
    assert all(l.by == UIA for l in SET_AS_RELAY_LOCATORS)


def test_dialog_is_not_scrollable():
    # A dialog fits one screen: no scroll-into-view needed.
    assert SPEC.scrollable is False


def test_title_and_body_assert_the_case_copy():
    # These two intentionally encode the TestRail copy (so they fail on a build whose
    # copy differs) rather than asserting mere element presence.
    by_name = _by_name()
    assert "Set as Relay?" in by_name["dialog_title"].value
    assert "pair directly without manually resetting relay mode" in \
        by_name["dialog_body"].value


def test_buttons_bind_role_id_and_label():
    by_name = _by_name()
    assert 'resourceId("android:id/button2")' in by_name["cancel_button"].value
    assert 'text("Cancel")' in by_name["cancel_button"].value
    assert 'resourceId("android:id/button1")' in by_name["set_as_relay_button"].value
    assert 'text("Set as Relay")' in by_name["set_as_relay_button"].value


def test_stub_mode_returns_canned_pass():
    result = verify_set_as_relay_dialog(StubWebDriver(), stub=True)
    assert result.passed
    assert result.failures == []
    assert {r.name for r in result.results} == EXPECTED_COMPONENTS


def test_stub_mode_honors_stub_returns():
    result = verify_set_as_relay_dialog(StubWebDriver(), stub=True,
                                        stub_returns=["forced failure"])
    assert not result.passed
    assert result.failures == ["forced failure"]


def _all_present_driver():
    present = {l.as_tuple() for l in SET_AS_RELAY_LOCATORS}
    return StubWebDriver(present=present, present_all=False)


def test_real_path_all_present_passes_strict():
    # Engine wiring: when every (spec-text) locator resolves, the dialog passes.
    result = verify_set_as_relay_dialog(_all_present_driver(), stub=False,
                                        lenient_if_unconfirmed=False)
    assert result.passed, result.failures
    assert len(result.results) == 4


def test_real_path_missing_copy_fails_strict():
    # Drop the two copy-asserting locators (as a build with different copy would):
    # they fail strictly, the two buttons still pass.
    present = {l.as_tuple() for l in SET_AS_RELAY_LOCATORS
               if l.name in ("cancel_button", "set_as_relay_button")}
    driver = StubWebDriver(present=present, present_all=False)
    result = verify_set_as_relay_dialog(driver, stub=False,
                                        lenient_if_unconfirmed=False)
    assert not result.passed
    assert any("dialog_title" in f for f in result.failures)
    assert any("dialog_body" in f for f in result.failures)
