from atak_lib.session.stub_driver import StubWebDriver
from atak_lib.ui.base import ScreenVerificationResult, UICommand
from atak_lib.ui.locators import UNCONFIRMED, BY_ID, Locator
from atak_lib.ui.verify_onboarding_screen import ONBOARDING_LOCATORS, verify_onboarding_screen

ALL_NAMES = {l.name for l in ONBOARDING_LOCATORS}


def test_empty_screen_no_longer_tolerated_all_confirmed():
    # Every onboarding locator is now hardware-CONFIRMED, so leniency no longer
    # applies: an empty screen fails outright with nothing tolerated.
    result = verify_onboarding_screen(StubWebDriver(present_all=False), stub=False)
    assert not result.passed
    assert {r.name for r in result.tolerated} == set()


def test_tripwire_flags_unconfirmed_locator_as_tolerated():
    # Mechanism check, independent of the now all-CONFIRMED spec: an UNCONFIRMED
    # locator absent under default leniency passes-but-tolerated (the tripwire).
    cmd = UICommand(StubWebDriver(present_all=False), stub=False)
    result = ScreenVerificationResult(screen="t")
    cmd.check_locator(result, Locator("x", BY_ID, "com.gotenna.atak:id/x", UNCONFIRMED),
                      lenient_if_unconfirmed=True)
    assert result.passed
    assert [r.name for r in result.tolerated] == ["x"]
    assert "tolerated [would fail under strict]" in result.summary()


def test_no_tolerated_when_screen_is_correct():
    by = {l.name: l for l in ONBOARDING_LOCATORS}
    present = {l.as_tuple() for l in ONBOARDING_LOCATORS}
    attrs = {by["login_button"].as_tuple(): {"enabled": "true"}}
    driver = StubWebDriver(present=present, present_all=False, attributes=attrs)
    result = verify_onboarding_screen(driver, stub=False)
    assert result.passed
    assert result.tolerated == []
