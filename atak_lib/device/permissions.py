"""ATAK permission pre-grant -- salvaged from QWIK's PermissionGranter.

Pre-granting runtime permissions via ``adb shell pm grant`` BEFORE an Appium
session keeps permission dialogs from overlapping the screen under test (the
onboarding permission-overlap risk @ui-comprehensive-tester flagged). Pure
adb/subprocess: no Appium, no env reads. The permission sets and API/version
gating are salvaged knowledge from QWIK (src/appium/utils/PermissionGranter.ts);
see docs/salvaged_locators.md section 9. The command runner is injectable so this
is unit-testable offline.
"""
from __future__ import annotations

import logging
import subprocess
from typing import Callable, List, Optional, Tuple

from atak_lib.session.capabilities import ATAK_CORE_PACKAGE, PLUGIN_PACKAGE

log = logging.getLogger(__name__)

Runner = Callable[[List[str]], str]
GrantResult = Tuple[str, bool, str]  # (permission, ok, error)


def _default_runner(argv: List[str]) -> str:
    return subprocess.check_output(argv, stderr=subprocess.DEVNULL).decode("utf-8", "ignore")


# Core ATAK permissions always granted (QWIK grantCorePermissions).
CORE_ALWAYS = [
    "android.permission.ACCESS_FINE_LOCATION",
    "android.permission.READ_PHONE_NUMBERS",
    "android.permission.READ_EXTERNAL_STORAGE",
    "android.permission.ACCESS_COARSE_LOCATION",
    "android.permission.READ_PHONE_STATE",
    "android.permission.CAMERA",
    "android.permission.WRITE_EXTERNAL_STORAGE",
    "android.permission.RECORD_AUDIO",
    "android.permission.ACCESS_BACKGROUND_LOCATION",
    "android.permission.ACCESS_MEDIA_LOCATION",
]
BLUETOOTH_API12 = [
    "android.permission.BLUETOOTH_CONNECT",
    "android.permission.BLUETOOTH_ADVERTISE",
    "android.permission.BLUETOOTH_SCAN",
]
MEDIA_API13 = [
    "android.permission.NEARBY_WIFI_DEVICES",
    "android.permission.POST_NOTIFICATIONS",
    "android.permission.READ_MEDIA_IMAGES",
    "android.permission.READ_MEDIA_AUDIO",
    "android.permission.READ_MEDIA_VIDEO",
]
VISUAL_API14 = ["android.permission.READ_MEDIA_VISUAL_USER_SELECTED"]
SEND_SMS = "android.permission.SEND_SMS"          # removed in ATAK 5.5
MANAGE_EXTERNAL_STORAGE = "MANAGE_EXTERNAL_STORAGE"  # via appops, not pm grant
PLUGIN_API13 = ["android.permission.POST_NOTIFICATIONS"]


def _version_lt(version: str, target: str) -> bool:
    def parse(v: str) -> Tuple[int, ...]:
        nums = []
        for part in v.split("."):
            digits = "".join(c for c in part if c.isdigit())
            nums.append(int(digits) if digits else 0)
        return tuple(nums)
    return parse(version) < parse(target)


def core_permissions(api_level: int, atak_version: Optional[str] = None) -> List[str]:
    """Core ATAK permission list for a device API level + ATAK version."""
    perms = list(CORE_ALWAYS)
    if api_level >= 12:
        perms += BLUETOOTH_API12
    if api_level >= 13:
        perms += MEDIA_API13
    if api_level >= 14:
        perms += VISUAL_API14
    # SEND_SMS only for ATAK < 5.5 (unknown version -> assume pre-5.5, QWIK behavior).
    if atak_version is None or _version_lt(atak_version, "5.5"):
        perms.append(SEND_SMS)
    return perms


def plugin_permissions(api_level: int) -> List[str]:
    """goTenna plugin permission list (POST_NOTIFICATIONS only, API >= 13)."""
    return list(PLUGIN_API13) if api_level >= 13 else []


class Permissions:
    """Pre-grant ATAK/plugin permissions via adb. Runner injectable for tests."""

    def __init__(self, runner: Runner = _default_runner):
        self._run = runner

    def pregrant(self, udid: str, package: str, permissions: List[str]) -> List[GrantResult]:
        """Grant each permission; collect per-permission outcome (never raises)."""
        results: List[GrantResult] = []
        for perm in permissions:
            try:
                self._run(["adb", "-s", udid, "shell", "pm", "grant", package, perm])
                results.append((perm, True, ""))
            except Exception as exc:  # noqa: BLE001 -- mirror QWIK allSettled
                log.warning("Failed to grant %s to %s on %s: %s", perm, package, udid, exc)
                results.append((perm, False, str(exc)))
        return results

    def pregrant_core(self, udid: str, api_level: int,
                      package: str = ATAK_CORE_PACKAGE,
                      atak_version: Optional[str] = None) -> List[GrantResult]:
        results = self.pregrant(udid, package, core_permissions(api_level, atak_version))
        try:
            self._run(["adb", "-s", udid, "shell", "appops", "set",
                       package, MANAGE_EXTERNAL_STORAGE, "allow"])
            results.append((MANAGE_EXTERNAL_STORAGE, True, ""))
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed appops MANAGE_EXTERNAL_STORAGE on %s: %s", udid, exc)
            results.append((MANAGE_EXTERNAL_STORAGE, False, str(exc)))
        return results

    def pregrant_plugin(self, udid: str, api_level: int,
                        package: str = PLUGIN_PACKAGE) -> List[GrantResult]:
        return self.pregrant(udid, package, plugin_permissions(api_level))
