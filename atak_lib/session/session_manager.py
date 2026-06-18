"""Session lifecycle for one or more ATAK devices.

Key contract: the ``stub`` flag is *injected* by the caller (an adapter). This
module never reads ``ATAK_STUB_MODE`` or any environment variable -- that is the
adapter layer's job. Stub mode yields :class:`StubWebDriver` instances; real
mode lazily imports Appium so that stub/CI runs need no Appium install.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from atak_lib.session.capabilities import (
    DEFAULT_APPIUM_SERVER,
    MOCK_LOCATION,
    build_capabilities,
)
from atak_lib.session.stub_driver import StubWebDriver

log = logging.getLogger(__name__)


class DeviceSpec:
    """A device to drive: a udid plus the platformVersion for its caps."""

    def __init__(self, udid: str, platform_version: str = "0",
                 host_variant: str = "civ", role: str = "",
                 caps_overrides: Optional[Dict[str, Any]] = None):
        self.udid = udid
        self.platform_version = platform_version
        self.host_variant = host_variant   # "civ" | "mil"
        self.role = role                    # e.g. GT1/GT2/GT3 (multi-device topology)
        self.caps_overrides = caps_overrides or {}


class SessionManager:
    def __init__(
        self,
        devices: List[DeviceSpec],
        *,
        stub: bool,
        server_url: str = DEFAULT_APPIUM_SERVER,
        driver_factory: Optional[Callable[[DeviceSpec], Any]] = None,
    ):
        if stub not in (True, False):
            raise ValueError("stub must be an explicit bool injected by the adapter")
        self.devices = devices
        self.stub = stub
        self.server_url = server_url
        self._driver_factory = driver_factory or self._default_driver_factory
        self.drivers: List[Any] = []

    # -- lifecycle ---------------------------------------------------------
    def start(self) -> List[Any]:
        self.drivers = [self._driver_factory(spec) for spec in self.devices]
        log.info("Started %d driver(s) (stub=%s)", len(self.drivers), self.stub)
        return self.drivers

    def stop(self) -> None:
        for driver in self.drivers:
            try:
                driver.quit()
            except Exception as exc:  # never let teardown raise
                log.warning("Error quitting driver: %s", exc)
        self.drivers = []

    def __enter__(self) -> "SessionManager":
        self.start()
        return self

    def __exit__(self, *exc_info) -> None:
        self.stop()

    @property
    def driver(self) -> Any:
        if not self.drivers:
            raise RuntimeError("Session not started; call start() first.")
        return self.drivers[0]

    # -- factories ---------------------------------------------------------
    def _default_driver_factory(self, spec: DeviceSpec) -> Any:
        if self.stub:
            return StubWebDriver(udid=spec.udid)
        return self._build_real_driver(spec)

    def _build_real_driver(self, spec: DeviceSpec) -> Any:
        # Lazy imports: stub/CI runs must not require Appium to be installed.
        from appium import webdriver  # type: ignore

        platform_version = spec.platform_version
        if platform_version in (None, "", "0"):
            from atak_lib.device.adb import ADB
            platform_version = ADB().get_os_version(spec.udid)

        caps = build_capabilities(
            spec.udid, platform_version, spec.host_variant, **spec.caps_overrides
        )
        driver = self._remote(webdriver, caps)
        try:
            driver.set_location(*MOCK_LOCATION)
        except Exception as exc:
            log.warning("Could not set mock location: %s", exc)
        return driver

    def _remote(self, webdriver: Any, caps: Dict[str, Any]) -> Any:
        """Open an Appium session, tolerant of the client v2 vs v3 signature.

        Appium-Python-Client v3 takes ``options=<UiAutomator2Options>`` and
        rejects a raw caps dict; v2 takes the caps dict positionally. We pin v2
        in pyproject, but handle both so a client upgrade doesn't break bring-up.
        """
        try:
            from appium.options.android import UiAutomator2Options  # type: ignore
            options = UiAutomator2Options().load_capabilities(caps)
            return webdriver.Remote(self.server_url, options=options)
        except Exception as exc:  # v2 client, or options path unavailable
            log.info("Falling back to positional capabilities (Appium client v2): %s", exc)
            return webdriver.Remote(self.server_url, caps)
