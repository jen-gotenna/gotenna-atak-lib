"""Screen -- the consumer-facing UI manipulation + state facade.

Resolves named selectors from the catalog (:mod:`atak_lib.selectors`) and drives an
**injected** Appium WebDriver. It exposes:

* **manipulation** -- ``tap``, ``type``, ``wait_for``, ``scroll_into_view``
* **state queries** -- ``is_present``, ``is_enabled``, ``get_text`` (return **facts**)

It never asserts or returns pass/fail -- judging expected results is the consuming
test framework's job (RFC 0001). Works identically against a real Appium driver, a
``SessionManager``-created one, or ``StubWebDriver``; the lib depends only on the
WebDriver interface (``find_element`` / ``find_elements`` + element ``click`` /
``send_keys`` / ``text`` / ``is_enabled``).
"""
from __future__ import annotations

import time
from typing import Any, Optional, Tuple, Union

from atak_lib.selectors import SelectorCatalog, load_catalog
from atak_lib.ui.locators import BY_ID

_ANDROID_UIAUTOMATOR = "-android uiautomator"


class Screen:
    def __init__(
        self,
        screen: Union[str, SelectorCatalog],
        driver: Any,
        *,
        version: Optional[str] = None,
        timeout: float = 10.0,
        poll_interval: float = 0.25,
    ):
        """``screen`` is a dotted catalog name (``"ui.onboarding"``, loaded from the
        package) or a :class:`SelectorCatalog` (a consumer's own). ``driver`` is the
        injected Appium WebDriver. ``version`` resolves version-specific selectors."""
        self.driver = driver
        self.version = version
        self.timeout = timeout
        self.poll_interval = poll_interval
        if isinstance(screen, SelectorCatalog):
            self._catalog = screen
            self.screen = screen.screen
        else:
            self.screen = screen
            self._catalog = load_catalog(screen)

    def locator(self, element: str) -> Tuple[str, str]:
        """The resolved ``(by, value)`` for ``element`` on this screen/version."""
        return self._catalog.locator(element, self.version)

    def find(self, element: str) -> Any:
        """Find one element (raises if absent -- use for elements known present)."""
        by, value = self.locator(element)
        return self.driver.find_element(by, value)

    def find_all(self, element: str) -> Any:
        """All matching elements ([] if none) -- the no-raise presence primitive."""
        by, value = self.locator(element)
        return self.driver.find_elements(by, value)

    # --- state queries (facts, never assertions) ---
    def is_present(self, element: str) -> bool:
        return len(self.find_all(element)) > 0

    def is_enabled(self, element: str) -> bool:
        return bool(self.find(element).is_enabled())

    def get_text(self, element: str) -> str:
        return self.find(element).text or ""

    # --- manipulation ---
    def tap(self, element: str) -> "Screen":
        self.find(element).click()
        return self

    def type(self, element: str, text: str, *, clear: bool = True) -> "Screen":
        el = self.find(element)
        if clear:
            el.clear()
        el.send_keys(text)
        return self

    def wait_for(self, element: str, *, timeout: Optional[float] = None) -> bool:
        """Poll until ``element`` is present or the timeout elapses. Returns whether
        it appeared. ``timeout=0`` checks exactly once."""
        deadline = time.monotonic() + (self.timeout if timeout is None else timeout)
        while True:
            if self.is_present(element):
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(self.poll_interval)

    def scroll_into_view(self, element: str) -> bool:
        """Best-effort UiAutomator2 scroll-to-element; returns whether it's then
        present. Guarded: on a driver that can't scroll (e.g. StubWebDriver) the
        scroll call is swallowed and this is just a presence check, so offline
        behavior is unchanged. Only id selectors are scrolled (UiScrollable)."""
        by, value = self.locator(element)
        if by == BY_ID:
            scroll = (
                'new UiScrollable(new UiSelector().scrollable(true))'
                '.scrollIntoView(new UiSelector().resourceId("%s"))' % value
            )
            try:
                self.driver.find_element(_ANDROID_UIAUTOMATOR, scroll)
            except Exception:
                pass
        return self.is_present(element)
