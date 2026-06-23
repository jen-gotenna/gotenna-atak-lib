"""Opt-in real-device smoke for the Screen facade against the onboarding screen.

Deselected by default: skips unless ``ATAK_DEVICE_SMOKE=1`` and ``ATAK_SMOKE_UDID``
are set, an Appium server is running, and the plugin is at the onboarding screen.
Mirrors the framework's ``parallel_smoke`` opt-in pattern -- the Screen/catalog logic
is unit-covered offline (test_screen.py, test_selectors.py); this confirms the SAME
calls bind real UiAutomator2 selectors on a real ATAK build.

Read-only: presence/text/enabled + scroll only; no taps, no app reset.

Recorded green 2026-06-22 on SM-S721U / com.gotenna.atak 3.0.0 (859d398a): 10/10
onboarding selectors resolved, text matched spec, login_button enabled,
scroll_into_view found.

    ATAK_DEVICE_SMOKE=1 ATAK_SMOKE_UDID=<udid> \
      python -m pytest tests/unit/test_device_smoke.py -m device_smoke -q
"""
import os

import pytest

pytestmark = pytest.mark.device_smoke

ONBOARDING = [
    "logo", "logo_subtext", "login_button", "login_subtext",
    "deploy_qr_button", "deploy_qr_subtext", "manual_setup_button",
    "manual_setup_subtext", "terms_of_service_checkbox", "terms_of_service_text",
]


def test_onboarding_selectors_resolve_on_device():
    if os.environ.get("ATAK_DEVICE_SMOKE") != "1" or not os.environ.get("ATAK_SMOKE_UDID"):
        pytest.skip("opt-in: set ATAK_DEVICE_SMOKE=1 + ATAK_SMOKE_UDID, Appium on :4723, "
                    "plugin at onboarding")
    # Imported here (not at module load) so CI collection needs no Appium install.
    from appium import webdriver
    from appium.options.android import UiAutomator2Options

    from atak_lib import Screen

    server = os.environ.get("ATAK_SMOKE_APPIUM", "http://127.0.0.1:4723")
    opts = UiAutomator2Options()
    opts.platform_name = "Android"
    opts.automation_name = "UiAutomator2"
    opts.set_capability("appium:udid", os.environ["ATAK_SMOKE_UDID"])
    opts.set_capability("appium:noReset", True)          # never clear app data
    opts.set_capability("appium:forceAppLaunch", False)  # attach; don't disturb onboarding
    opts.set_capability("appium:newCommandTimeout", 120)

    driver = webdriver.Remote(server, options=opts)
    try:
        s = Screen("ui.onboarding", driver)
        missing = [e for e in ONBOARDING if not s.is_present(e)]
        assert not missing, f"onboarding selectors not resolved on device: {missing}"
        assert s.is_enabled("login_button")
        assert s.get_text("terms_of_service_text")          # non-empty real text
        assert s.scroll_into_view("terms_of_service_text")  # real UiAutomator2 scroll
    finally:
        driver.quit()
