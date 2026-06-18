"""ADB helpers, extracted and cleaned from legacy utils/adb.py and utils/appium.py.

Pure subprocess/ADB -- no Appium dependency. The command runner is injectable
(`runner=`) so these helpers are unit-testable offline with a fake runner; the
default shells out to real `adb`. This module reads no environment variables.
"""
from __future__ import annotations

import logging
import re
import subprocess
from typing import Callable, Dict, List

from atak_lib.session.capabilities import ATAK_CORE_PACKAGE, PLUGIN_PACKAGE

log = logging.getLogger(__name__)

# A runner takes an argv list and returns decoded stdout.
Runner = Callable[[List[str]], str]


def _default_runner(argv: List[str]) -> str:
    return subprocess.check_output(argv, stderr=subprocess.DEVNULL).decode("utf-8", "ignore")


class ADB:
    def __init__(self, runner: Runner = _default_runner):
        self._run = runner

    def _adb(self, udid: str, *args: str) -> str:
        return self._run(["adb", "-s", udid, *args])

    def get_os_version(self, udid: str) -> str:
        """Android release string (legacy: getprop ro.build.version.release)."""
        return self._adb(udid, "shell", "getprop", "ro.build.version.release").strip()

    def get_api_level(self, udid: str) -> int:
        """Android API level (getprop ro.build.version.sdk) -- used to select the
        version-gated permission set. Returns 0 if unreadable."""
        out = self._adb(udid, "shell", "getprop", "ro.build.version.sdk").strip()
        return int(out) if out.isdigit() else 0

    def get_plugin_version(self, udid: str) -> str:
        """goTenna plugin versionName via dumpsys (legacy regex versionName=X.Y.Z)."""
        out = self._adb(udid, "shell", "dumpsys", "package", PLUGIN_PACKAGE)
        match = re.search(r"versionName=([0-9]+\.[0-9]+\.[0-9]+)", out)
        if match:
            return match.group(1)
        log.error("Plugin versionName not found for %s", udid)
        return "unknown"

    def get_versions(self, udid: str) -> Dict[str, str]:
        """Core + plugin versions and Playstore detection (legacy get_versions)."""
        core = self._adb(udid, "shell", "dumpsys", "package", ATAK_CORE_PACKAGE)
        plugin = self._adb(udid, "shell", "dumpsys", "package", PLUGIN_PACKAGE)

        def _name(text: str) -> str:
            m = re.search(r"versionName=(\S+)", text)
            return m.group(1) if m else "unknown"

        def _code(text: str) -> str:
            m = re.search(r"versionCode=(\d+)", text)
            return m.group(1) if m else "unknown"

        return {
            "core_version": _name(core),
            "build_type": "Playstore" if "playstore" in core.lower() else "Non-Playstore",
            "plugin_version": _name(plugin),
            "build_number": _code(plugin),
        }

    def is_app_crashed(self, udid: str) -> bool:
        """True if ATAK core is absent from the process list (legacy is_app_crashed)."""
        out = self._adb(udid, "shell", "ps")
        return ATAK_CORE_PACKAGE not in out
