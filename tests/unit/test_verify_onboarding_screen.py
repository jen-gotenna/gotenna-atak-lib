from atak_lib.session.stub_driver import StubWebDriver
from atak_lib.ui.base import ScreenVerificationResult, UICommand
from atak_lib.ui.locators import CONFIRMED, CROSS_CONFIRMED, UNCONFIRMED, BY_ID, Locator
from atak_lib.ui.verify_onboarding_screen import (
    ONBOARDING_LOCATORS,
    TARGET_PLUGIN_VERSION,
    TESTRAIL_CASE_ID,
    verify_onboarding_screen,
)

EXPECTED_COMPONENTS = {
    "logo", "logo_subtext",
    "login_button", "login_subtext",
    "deploy_qr_button", "deploy_qr_subtext",
    "manual_setup_button", "manual_setup_subtext",
    "terms_of_service_checkbox", "terms_of_service_text",
}


def _by_name():
    return {l.name: l for l in ONBOARDING_LOCATORS}


def test_targets_plugin_3_0_and_case_c147673():
    assert TARGET_PLUGIN_VERSION == "3.0"
    assert TESTRAIL_CASE_ID == "C147673"


def test_components_match_testrail_case():
    assert {l.name for l in ONBOARDING_LOCATORS} == EXPECTED_COMPONENTS
    assert len(ONBOARDING_LOCATORS) == 10


def test_all_components_present_on_atak_plugin():
    # On the ATAK plugin every C147673 component is present (the "Not available on
    # Pro App 3.1.0" notations are Pro-App-scoped, handled in the proapp sample).
    assert all(l.expected_present for l in ONBOARDING_LOCATORS)


def test_all_locators_confirmed_on_hardware():
    # Promoted from the QWIK cross-tool tier after a real 3.0.0 hardware session.
    by = _by_name()
    statuses = {l.status for l in ONBOARDING_LOCATORS}
    assert statuses == {CONFIRMED}
    assert CROSS_CONFIRMED not in statuses
    assert UNCONFIRMED not in statuses
    assert by["login_button"].value == "com.gotenna.atak:id/loginButton"
    assert by["terms_of_service_checkbox"].value == "com.gotenna.atak:id/termsCheckbox"


def test_login_button_expected_enabled():
    assert _by_name()["login_button"].expect_enabled is True


def test_terms_text_matches_build_string_not_case():
    # Selector is now a stable resource-id (no xpath); the build copy lives in the
    # locator note. Build renders "Service"; C147673 says "Use" (see known_gaps).
    loc = _by_name()["terms_of_service_text"]
    assert loc.by == BY_ID
    assert loc.value == "com.gotenna.atak:id/termsCheckboxText"
    assert "I agree to the Terms of Service" in loc.note


def test_case_subtext_strings_documented_in_notes():
    # The subtext copy moved from the (removed) text-xpath into the locator note.
    by = _by_name()
    assert "Please select a deployment option below" in by["logo_subtext"].note
    assert "Login with a Portal account." in by["login_subtext"].note
    assert "Scan a user provided QR Code." in by["deploy_qr_subtext"].note
    assert "Take me right into the app." in by["manual_setup_subtext"].note


def test_stub_mode_returns_canned_pass():
    result = verify_onboarding_screen(StubWebDriver(), stub=True)
    assert result.passed
    assert result.failures == []
    assert {r.name for r in result.results} == EXPECTED_COMPONENTS


def test_stub_mode_honors_stub_returns():
    result = verify_onboarding_screen(StubWebDriver(), stub=True,
                                      stub_returns=["forced failure"])
    assert not result.passed
    assert result.failures == ["forced failure"]


def _full_screen_driver():
    by = _by_name()
    present = {l.as_tuple() for l in ONBOARDING_LOCATORS}      # all 10 present
    attrs = {by["login_button"].as_tuple(): {"enabled": "true"}}
    return StubWebDriver(present=present, present_all=False, attributes=attrs)


def test_real_path_full_screen_passes_strict():
    result = verify_onboarding_screen(_full_screen_driver(), stub=False,
                                      lenient_if_unconfirmed=False)
    assert result.passed, result.failures
    assert len(result.results) == 10


def test_real_path_missing_present_component_fails_strict():
    by = _by_name()
    present = {l.as_tuple() for l in ONBOARDING_LOCATORS
               if l.name != "deploy_qr_button"}             # drop one present component
    attrs = {by["login_button"].as_tuple(): {"enabled": "true"}}
    driver = StubWebDriver(present=present, present_all=False, attributes=attrs)
    result = verify_onboarding_screen(driver, stub=False, lenient_if_unconfirmed=False)
    assert not result.passed
    assert any("deploy_qr_button" in f and "not found" in f for f in result.failures)


def test_real_path_flags_login_disabled_when_strict():
    by = _by_name()
    present = {l.as_tuple() for l in ONBOARDING_LOCATORS}
    attrs = {by["login_button"].as_tuple(): {"enabled": "false"}}  # wrong state
    driver = StubWebDriver(present=present, present_all=False, attributes=attrs)
    result = verify_onboarding_screen(driver, stub=False, lenient_if_unconfirmed=False)
    assert not result.passed
    assert any("login_button" in f and "expected enabled" in f for f in result.failures)


def test_empty_screen_fails_now_that_all_confirmed():
    # All 10 are hardware-CONFIRMED -> strict even under default leniency, so an
    # empty screen fails outright with nothing tolerated.
    result = verify_onboarding_screen(StubWebDriver(present_all=False), stub=False)
    assert not result.passed
    assert len(result.failures) == 10
    assert result.tolerated == []


def test_confirmed_locator_is_strict_when_promoted():
    driver = StubWebDriver(present_all=False)
    cmd = UICommand(driver, stub=False)
    result = ScreenVerificationResult(screen="t")
    cmd.check_locator(result, Locator("x", BY_ID, "com.gotenna.atak:id/x", CONFIRMED))
    assert not result.passed
    assert "x" in result.failures[0]
