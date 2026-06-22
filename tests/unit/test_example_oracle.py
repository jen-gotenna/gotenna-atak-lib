"""Keep the reference consumer-oracle example honest (it doubles as living docs)."""
from examples.consumer_oracle import ONBOARDING_EXPECTED, check_onboarding
from atak_lib.selectors import load_catalog
from atak_lib.session.stub_driver import StubWebDriver


def test_oracle_passes_on_a_full_screen():
    # Every selector present + Login enabled -> no failures.
    assert check_onboarding(StubWebDriver(present_all=True)) == []


def test_oracle_reports_each_missing_component():
    # Nothing present -> one failure per expected component.
    drv = StubWebDriver(present_all=False, present=set())
    failures = check_onboarding(drv)
    assert len(failures) == len(ONBOARDING_EXPECTED)
    assert all(f.startswith("missing component:") for f in failures)


def test_oracle_flags_disabled_login():
    login = load_catalog("ui.onboarding").locator("login_button")  # (by, value)
    drv = StubWebDriver(present_all=True, attributes={login: {"enabled": "false"}})
    failures = check_onboarding(drv)
    assert failures == ["login_button is present but not enabled"]


def test_expected_set_matches_catalog():
    # The consumer's expectations reference real catalog elements (no drift).
    catalog_elements = set(load_catalog("ui.onboarding").selectors)
    assert set(ONBOARDING_EXPECTED) <= catalog_elements
