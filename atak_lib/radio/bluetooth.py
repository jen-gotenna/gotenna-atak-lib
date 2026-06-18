"""Bluetooth / BLE control, cleaned from legacy common/pages/OS_page.py.

Changes vs legacy:
  * Per-udid and explicit -- the legacy versions looped over every PHONE* in the
    .env file. Multi-device fan-out now belongs to the driver_runner layer, not
    to these primitives, and no env is read here.
  * enable/disable wait for completion (subprocess.run) instead of fire-and-
    forget Popen, so callers can sequence reliably.
  * Runner is injectable for offline unit tests.
"""
from __future__ import annotations

import logging
import subprocess
from typing import Callable, List, Tuple

log = logging.getLogger(__name__)

Runner = Callable[[List[str]], str]


def _default_runner(argv: List[str]) -> str:
    return subprocess.check_output(argv, stderr=subprocess.DEVNULL).decode("utf-8", "ignore")


class Bluetooth:
    def __init__(self, runner: Runner = _default_runner):
        self._run = runner

    def enable_bluetooth(self, udid: str) -> None:
        log.info("Enabling Bluetooth on %s", udid)
        self._run(["adb", "-s", udid, "shell", "svc", "bluetooth", "enable"])

    def disable_bluetooth(self, udid: str) -> None:
        log.info("Disabling Bluetooth on %s", udid)
        self._run(["adb", "-s", udid, "shell", "svc", "bluetooth", "disable"])

    def get_BLE_status(self, udid: str) -> Tuple[str, str]:
        """Return (status, message) where status is 'on' | 'off' | 'unknown'.

        Parses `dumpsys bluetooth_manager` for the `enabled:` line (legacy logic).
        """
        out = self._run(
            ["adb", "-s", udid, "shell", "dumpsys", "bluetooth_manager"]
        ).lower()
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("enabled:"):
                if "true" in line:
                    return "on", "Bluetooth is enabled"
                if "false" in line:
                    return "off", "Bluetooth is disabled"
        return "unknown", "Bluetooth status is unknown"

    def verify_BLE_on(self, udid: str) -> Tuple[bool, str]:
        status, message = self.get_BLE_status(udid)
        return status == "on", message

    def verify_BLE_off(self, udid: str) -> Tuple[bool, str]:
        status, message = self.get_BLE_status(udid)
        return status == "off", message
