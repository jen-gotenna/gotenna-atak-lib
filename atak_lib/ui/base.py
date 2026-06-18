"""Base machinery for UI assertion commands: soft assertions + presence checks.

Soft-assertion model: a command collects failures into a list and returns a
:class:`ScreenVerificationResult` rather than raising on the first miss, so a
single run reports every problem on a screen.

Presence checks use only ``driver.find_element(by, value)`` so they work against
both a real Appium driver and :class:`StubWebDriver`, with no Selenium import.
"""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from atak_lib.ui.locators import BY_ID, CONFIRMED, Locator

# Appium UiAutomator2 strategy for UiScrollable/UiSelector expressions.
_ANDROID_UIAUTOMATOR = "-android uiautomator"

log = logging.getLogger(__name__)


@dataclass
class AssertionResult:
    name: str
    status: str
    passed: bool
    message: str
    tolerated: bool = False   # passed ONLY because leniency suppressed a real miss


@dataclass
class ScreenVerificationResult:
    screen: str
    failures: List[str] = field(default_factory=list)
    results: List[AssertionResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failures

    def record(self, result: AssertionResult) -> None:
        self.results.append(result)
        if not result.passed:
            self.failures.append(result.message)

    @property
    def tolerated(self) -> List[AssertionResult]:
        """Checks that passed ONLY because lenient mode suppressed a real miss.

        These are the tripwire: green today, but they WOULD fail under strict
        (lenient_if_unconfirmed=False) -- e.g. on a real device once confirmed.
        """
        return [r for r in self.results if r.tolerated]

    def summary(self) -> str:
        parts = [f"{self.screen}: {'PASS' if self.passed else 'FAIL'}",
                 f"{len(self.results)} checks", f"{len(self.failures)} failed"]
        n = len(self.tolerated)
        if n:
            parts.append(f"{n} tolerated [would fail under strict]")
        return " | ".join(parts)


class UICommand:
    """Base for UI commands. The ``stub`` flag is injected, never read from env."""

    screen_name = "screen"

    def __init__(self, driver: Any, *, stub: bool = False, scrollable: bool = False):
        self.driver = driver
        self.stub = stub
        # When True, locate() scrolls a long screen to bring an off-screen element
        # into view before deciding it is absent. Default False keeps single-screen
        # commands (e.g. onboarding) byte-for-byte identical to the prior behavior.
        self.scrollable = scrollable

    def _locate(self, locator: Locator) -> Optional[Any]:
        """Find a locator's element, scrolling it into view on long screens.

        Returns the element, or None if not found. The scroll path is best-effort
        and fully guarded: on a driver that can't scroll (e.g. StubWebDriver) every
        scroll call raises and is swallowed, so the result is exactly the plain
        ``find_element`` outcome -- offline/stub behavior is unchanged.
        """
        try:
            return self.driver.find_element(locator.by, locator.value)
        except Exception:
            pass
        # FALLBACK only. For a scrollable screen the PRIMARY route is
        # ScreenCommand._snapshot_presence() in verify() (page_source snapshots +
        # bounded in-pane swipes). This per-locator scrollIntoView runs only when
        # that route is unavailable -- e.g. page_source raised, or a non-id locator
        # (the snapshot path resolves id locators only). It is slower on ATAK's tree,
        # which is why it is not the default.
        if self.scrollable and locator.by == BY_ID:
            scroll = (
                'new UiScrollable(new UiSelector().scrollable(true))'
                '.scrollIntoView(new UiSelector().resourceId("%s"))' % locator.value
            )
            try:
                self.driver.find_element(_ANDROID_UIAUTOMATOR, scroll)
                return self.driver.find_element(locator.by, locator.value)
            except Exception:
                return None
        return None

    def _page_ids(self) -> Optional[Dict[str, Dict[str, str]]]:
        """Parse the current page_source into ``{resource-id: attrs}``.

        Returns None if page_source is unavailable (e.g. StubWebDriver) or unparsable
        -- callers then fall back to per-locator find_element, so stub/offline runs
        are unaffected. Only the first node per resource-id is kept (sufficient for
        presence + the ``enabled`` attribute).
        """
        try:
            src = self.driver.page_source
        except Exception:
            return None
        try:
            root = ET.fromstring(src.encode("utf-8"))
        except Exception:
            return None
        out: Dict[str, Dict[str, str]] = {}
        for node in root.iter():
            rid = node.get("resource-id")
            if rid and rid not in out:
                out[rid] = node.attrib
        return out

    def _scroll_pane(self, down: bool = True) -> bool:
        """Swipe inside the scrollable pane's own bounds to reveal more of it.

        Deliberately a *bounded* swipe within the scroll container's rect -- NOT a
        center-screen swipe (which would hit the ATAK map), and NOT UiAutomator
        ``scrollIntoView`` (whose multi-swipe idle-waiting search costs ~3s on
        ATAK's never-idle tree even though the device scrolls in <1s). Returns False
        if there's no scrollable pane or the driver can't swipe (e.g. StubWebDriver).
        """
        try:
            els = self.driver.find_elements(
                _ANDROID_UIAUTOMATOR, "new UiSelector().scrollable(true)")
            rects = []
            for e in els:
                try:
                    rects.append(e.rect)
                except Exception:
                    pass
            if not rects:
                return False
            r = max(rects, key=lambda b: b["height"])   # the tall vertical scroller
            x = r["x"] + r["width"] // 2
            y_hi = r["y"] + int(r["height"] * 0.80)
            y_lo = r["y"] + int(r["height"] * 0.25)
            if down:
                self.driver.swipe(x, y_hi, x, y_lo, 150)   # content up -> reveal lower
            else:
                self.driver.swipe(x, y_lo, x, y_hi, 150)
            return True
        except Exception:
            return False

    def check_locator(
        self,
        result: ScreenVerificationResult,
        locator: Locator,
        *,
        lenient_if_unconfirmed: bool = True,
        presence: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> None:
        """Soft-assert a single locator into ``result``.

        Checks presence, and -- when ``locator.expect_enabled`` is set -- the
        element's enabled state (e.g. present-but-disabled). UNCONFIRMED problems
        (absent, wrong enabled-state, or undeterminable state) are recorded as
        passing-with-note when ``lenient_if_unconfirmed`` is set, so the suite
        stays green before the locators are hardware-verified. CONFIRMED locators
        are strict.

        ``presence`` is an optional ``{resource-id: attrs}`` snapshot (see
        :meth:`ScreenCommand._snapshot_presence`). When supplied, ``by: id`` locators
        are resolved from it -- no per-locator ``find_element`` round-trip. Any other
        strategy (xpath / -android uiautomator) still goes through ``_locate``.
        """
        tolerate = locator.status != CONFIRMED and lenient_if_unconfirmed

        def record(passed: bool, message: str) -> None:
            effective = passed or tolerate
            was_tolerated = (not passed) and tolerate
            note = "" if passed else (
                " (tolerated; awaiting hardware confirmation)" if tolerate else "")
            result.record(AssertionResult(
                locator.name, locator.status, effective,
                f"[{locator.status}] {locator.name}: {message}{note}",
                tolerated=was_tolerated,
            ))

        # Snapshot fast path for id locators; element path otherwise.
        from_snapshot = presence is not None and locator.by == BY_ID
        if from_snapshot:
            attrs = presence.get(locator.value)
            present = attrs is not None
            element = None
        else:
            element = self._locate(locator)
            attrs = None
            present = element is not None
        if not present:
            log.debug("%s not present (%s=%s)", locator.name, locator.by, locator.value)

        # Components expected to be removed for this release: assert ABSENT.
        if not locator.expected_present:
            if present:
                record(False, "expected absent (removed for this release) but found")
            else:
                record(True, "absent as expected (removed for this release)")
            return

        if not present:
            record(False, f"expected present but not found ({locator.by}={locator.value})")
            return

        if locator.expect_enabled is None:
            record(True, "present")
            return

        enabled_attr = attrs.get("enabled") if from_snapshot else element.get_attribute("enabled")
        if enabled_attr is None:
            record(False, "present but enabled-state could not be determined")
            return
        enabled = str(enabled_attr).lower() == "true"
        if enabled != locator.expect_enabled:
            want = "enabled" if locator.expect_enabled else "disabled"
            got = "enabled" if enabled else "disabled"
            record(False, f"present but expected {want}, was {got}")
            return
        state = "enabled" if enabled else "present-but-disabled"
        record(True, f"present and {state}")


class ScreenCommand(UICommand):
    """OOP, spec-driven screen verifier shared by every UI screen command.

    Holds a :class:`atak_lib.spec.CommandSpec` (locators loaded from YAML) and a
    driver, and runs the soft-assert loop once -- so individual commands carry no
    locator lists or assertion logic of their own (DRY). Subclass or instantiate
    directly; the registered command function is a thin wrapper around ``verify``.
    """

    def __init__(self, driver: Any, spec, *, stub: bool = False,
                 plugin_version: Optional[str] = None):
        # Resolve the spec for the target plugin version (injected by the adapter,
        # like `stub`). None => baseline spec unchanged, so existing single-version
        # callers behave exactly as before. atak_lib never DETECTS the version.
        if plugin_version and hasattr(spec, "for_version"):
            spec = spec.for_version(plugin_version)
        super().__init__(driver, stub=stub, scrollable=getattr(spec, "scrollable", False))
        self.spec = spec
        self.screen_name = spec.screen_name
        self.plugin_version = plugin_version

    def _snapshot_presence(self) -> Optional[Dict[str, Dict[str, str]]]:
        """Resolve all id-locator presence from page_source snapshots (fast path).

        A long screen exceeds one viewport, so one snapshot can't hold every
        locator. We snapshot the current view, then scroll the LAST id-locator into
        view and snapshot again (top+bottom usually covers the whole pane), then
        scroll any still-missing id-locator individually. This replaces ~N
        find_element round-trips with a couple of page_source dumps.

        Returns ``{resource-id: attrs}``, or None if page_source is unavailable
        (StubWebDriver / offline) so :meth:`verify` falls back to per-locator finds.
        """
        seen = self._page_ids()
        if seen is None:
            return None
        id_values = [l.value for l in self.spec.locators if l.by == BY_ID]

        # The pane may be left scrolled anywhere by a prior step, so first REWIND to
        # the top (swipe up until nothing new appears), then WALK DOWN accumulating
        # ids until everything's seen or the bottom stops revealing anything. Each
        # phase is bounded; together they cover the whole pane regardless of start.
        for _ in range(8):                       # rewind to top
            before = len(seen)
            if not self._scroll_pane(down=False):
                break
            more = self._page_ids()
            if more:
                seen.update(more)
            if len(seen) <= before:
                break
        for _ in range(8):                       # walk down
            if all(v in seen for v in id_values):
                break
            before = len(seen)
            if not self._scroll_pane(down=True):
                break
            more = self._page_ids()
            if more:
                seen.update(more)
            if len(seen) <= before:
                break
        return seen

    def verify(
        self,
        *,
        stub_returns: Optional[List[str]] = None,
        lenient_if_unconfirmed: bool = True,
    ) -> ScreenVerificationResult:
        result = ScreenVerificationResult(screen=self.spec.screen_name)

        if self.stub:
            # Canned results: every locator passes so per-component assertions
            # have something to read. Forced failures are added on top.
            for locator in self.spec.locators:
                result.results.append(AssertionResult(
                    locator.name, locator.status, True,
                    f"[{locator.status}] {locator.name}: present (stub)",
                ))
            failures = self.spec.stub_failures if stub_returns is None else list(stub_returns)
            result.failures.extend(failures)
            return result

        # Long screens: resolve id-locator presence via page_source snapshots once,
        # instead of a find_element per locator. None => fall back to per-locator.
        presence = self._snapshot_presence() if self.scrollable else None

        for locator in self.spec.locators:
            self.check_locator(result, locator,
                               lenient_if_unconfirmed=lenient_if_unconfirmed,
                               presence=presence)
        return result
