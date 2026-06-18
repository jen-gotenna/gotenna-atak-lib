from atak_lib.session.stub_driver import StubWebDriver
from atak_lib.ui.locators import CONFIRMED, BY_ID
from atak_lib.ui.verify_device_details_screen import (
    DEVICE_DETAILS_LOCATORS,
    SPEC,
    TARGET_PLUGIN_VERSION,
    TESTRAIL_CASE_ID,
    verify_device_details_screen,
)

# A representative slice of the C149719 component set (full set lives in the YAML).
KEY_COMPONENTS = {
    "status_text", "test_connection_button", "battery_text", "antenna_text",
    "operation_mode_text", "serial_text", "firmware_text", "change_firmware_button",
    "settings_modes_title", "relay_mode_tile", "led_mode_switch",
    "tether_mode_tile", "listen_only_mode_switch", "disconnect_button",
}


def _by_name():
    return {l.name: l for l in DEVICE_DETAILS_LOCATORS}


def test_targets_plugin_3_0_and_case_c149719():
    assert TARGET_PLUGIN_VERSION == "3.0"
    assert TESTRAIL_CASE_ID == "C149719"


def test_locators_are_confirmed_id_based_and_complete():
    assert len(DEVICE_DETAILS_LOCATORS) == 23
    assert all(l.status == CONFIRMED for l in DEVICE_DETAILS_LOCATORS)
    assert all(l.by == BY_ID for l in DEVICE_DETAILS_LOCATORS)   # xpath-free
    names = {l.name for l in DEVICE_DETAILS_LOCATORS}
    assert KEY_COMPONENTS <= names


def test_screen_marked_scrollable():
    # Long page: the verifier must scroll locators into view before asserting.
    assert SPEC.scrollable is True


def test_tether_present_on_plugin_pro_exclusion_is_proapp_scoped():
    # PRO-463 "Hidden for RC1" is a Pro-App exclusion; on the plugin Tether is present.
    assert _by_name()["tether_mode_tile"].expected_present is True


def test_stub_mode_returns_canned_pass():
    result = verify_device_details_screen(StubWebDriver(), stub=True)
    assert result.passed
    assert result.failures == []
    assert {r.name for r in result.results} == {l.name for l in DEVICE_DETAILS_LOCATORS}


def test_stub_mode_honors_stub_returns():
    result = verify_device_details_screen(StubWebDriver(), stub=True,
                                          stub_returns=["forced failure"])
    assert not result.passed
    assert result.failures == ["forced failure"]


def _full_screen_driver():
    present = {l.as_tuple() for l in DEVICE_DETAILS_LOCATORS}     # all 23 present
    return StubWebDriver(present=present, present_all=False)


def test_real_path_full_screen_passes_strict():
    # Even with scrollable=True, the guarded scroll path must degrade to a plain
    # presence check on a driver that can't scroll (StubWebDriver) -> all present.
    result = verify_device_details_screen(_full_screen_driver(), stub=False,
                                          lenient_if_unconfirmed=False)
    assert result.passed, result.failures
    assert len(result.results) == 23


def test_real_path_missing_component_fails_strict():
    present = {l.as_tuple() for l in DEVICE_DETAILS_LOCATORS
               if l.name != "listen_only_mode_switch"}           # drop one (below-fold)
    driver = StubWebDriver(present=present, present_all=False)
    result = verify_device_details_screen(driver, stub=False, lenient_if_unconfirmed=False)
    assert not result.passed
    assert any("listen_only_mode_switch" in f and "not found" in f for f in result.failures)


def test_scroll_path_does_not_raise_on_non_scrolling_driver():
    # Empty screen on a stub driver: the scroll-into-view attempts are swallowed and
    # the result is a clean set of "not found" failures, never an exception.
    result = verify_device_details_screen(StubWebDriver(present_all=False), stub=False,
                                          lenient_if_unconfirmed=False)
    assert not result.passed
    assert len(result.failures) == 23
    assert result.tolerated == []
