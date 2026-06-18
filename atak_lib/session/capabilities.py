"""Appium capability profile for the ATAK plugin.

Extracted and cleaned from the legacy suite (utils/appium.py ::
AppiumHelpers.start_appium_driver). Framework-agnostic: this module builds a
plain dict and never touches pytest, Robot, env vars, or a live driver.
"""
from __future__ import annotations

from typing import Any, Dict

# Plugin under test.
PLUGIN_PACKAGE = "com.gotenna.atak"

# ATAK host build (CIV vs MilTAK). The screen under test is "Common Functionality
# Between Apps" (C147673), so the suite must address both host builds.
#   civ  -- ATAK-CIV: package/activity CONFIRMED from the legacy suite.
#   mil  -- MilTAK:  PLACEHOLDER, UNCONFIRMED. The MilTAK package/activity have
#           NOT been verified; confirm on a MilTAK build (adb shell dumpsys /
#           `aapt dump badging`) before running against it.
HOST_PROFILES: Dict[str, Dict[str, Any]] = {
    "civ": {
        "package": "com.atakmap.app.civ",
        "activity": "com.atakmap.app.ATAKActivityCiv",
        "confirmed": True,
    },
    "mil": {
        # package cross-confirmed from QWIK SupportedPackages.ts (core set).
        "package": "com.atakmap.app.mil",
        "activity": "com.atakmap.app.ATAKActivity",  # TODO(hardware): confirm activity
        "confirmed": False,  # activity still unverified -> not launch-ready
    },
}
DEFAULT_HOST_VARIANT = "civ"

# Back-compat aliases (CIV is the historical default).
ATAK_CORE_PACKAGE = HOST_PROFILES["civ"]["package"]
ATAK_CORE_ACTIVITY = HOST_PROFILES["civ"]["activity"]

# Mock location used by the legacy suite (utils/appium.py :: set_location).
MOCK_LOCATION = (40.60809801682295, -74.00454064873787, 50)

DEFAULT_APPIUM_SERVER = "http://localhost:4723"


def host_profile(host_variant: str) -> Dict[str, Any]:
    try:
        return HOST_PROFILES[host_variant]
    except KeyError:
        raise ValueError(
            f"Unknown host_variant {host_variant!r}; expected one of "
            f"{sorted(HOST_PROFILES)}"
        )


def build_capabilities(
    udid: str,
    platform_version: str,
    host_variant: str = DEFAULT_HOST_VARIANT,
    **overrides: Any,
) -> Dict[str, Any]:
    """Return the UiAutomator2 capability dict for one device.

    ``platform_version`` is injected dynamically (legacy reads it via
    ``adb shell getprop ro.build.version.release``). ``host_variant`` selects the
    ATAK host build (``civ`` confirmed, ``mil`` placeholder). Pass ``overrides``
    to tweak individual capabilities without forking this profile.
    """
    profile = host_profile(host_variant)
    caps: Dict[str, Any] = {
        "platformName": "Android",
        "platformVersion": platform_version,
        "deviceName": udid,
        "udid": udid,
        "appActivity": profile["activity"],
        "appWaitActivity": profile["activity"],
        "appWaitDuration": 30000,
        "appPackage": profile["package"],
        "automationName": "UiAutomator2",
        "uiautomator2ServerLaunchTimeout": 20000,
        "disableWindowAnimation": True,
        "waitForIdleTimeout": 300,
        "noReset": True,
        "launch": True,
        "newCommandTimeout": 300,
    }
    caps.update(overrides)
    return caps
