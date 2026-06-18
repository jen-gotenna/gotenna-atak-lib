"""In-memory stand-in for an Appium WebDriver.

Lets the command library run with no device and no Appium/Selenium installed.
It implements only the surface the commands touch: ``find_element``,
``find_elements``, ``capabilities`` / ``desired_capabilities``, and ``quit``.

Two ways to use it:
  * Default: every locator is considered "present" (happy path for CI smoke).
  * Configured: pass ``present={(by, value), ...}`` to model a specific screen
    so the real assertion logic can be exercised offline.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Set, Tuple

Locator = Tuple[str, str]


class StubElement:
    def __init__(self, by: str, value: str, *, displayed: bool = True,
                 attributes: Optional[Dict[str, str]] = None, text: str = ""):
        self._by = by
        self._value = value
        self._displayed = displayed
        self._attributes = attributes or {}
        self.text = text

    def is_displayed(self) -> bool:
        return self._displayed

    def get_attribute(self, name: str) -> Optional[str]:
        return self._attributes.get(name)

    @property
    def size(self) -> Dict[str, int]:
        return {"width": 100, "height": 40}


class StubNoSuchElement(Exception):
    """Raised by StubWebDriver when a locator is not in the present set."""


class StubWebDriver:
    def __init__(
        self,
        udid: str = "STUBUDID",
        *,
        present: Optional[Iterable[Locator]] = None,
        present_all: bool = True,
        attributes: Optional[Dict[Locator, Dict[str, str]]] = None,
        texts: Optional[Dict[Locator, str]] = None,
    ):
        self._present_all = present_all
        self._present: Set[Locator] = set(present or set())
        self._attributes = attributes or {}
        self._texts = texts or {}
        self.capabilities: Dict[str, Any] = {"udid": udid}
        # Legacy code reads both spellings; mirror that for drop-in compatibility.
        self.desired_capabilities: Dict[str, Any] = {"udid": udid}
        self.quit_called = False

    def _is_present(self, by: str, value: str) -> bool:
        if self._present_all:
            return True
        return (by, value) in self._present

    def find_element(self, by: str, value: str) -> StubElement:
        if not self._is_present(by, value):
            raise StubNoSuchElement(f"{by}={value}")
        return StubElement(
            by, value,
            attributes=self._attributes.get((by, value), {}),
            text=self._texts.get((by, value), ""),
        )

    def find_elements(self, by: str, value: str):
        try:
            return [self.find_element(by, value)]
        except StubNoSuchElement:
            return []

    def quit(self) -> None:
        self.quit_called = True
