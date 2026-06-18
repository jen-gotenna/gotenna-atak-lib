"""Locator model shared by all UI commands.

A Locator carries its Appium strategy/value plus a confirmation `status`:
  CONFIRMED   - selector verified by US on the target build (hardware/Appium
                Inspector). The engine asserts CONFIRMED locators strictly.
  CROSS_CONFIRMED - selector verified by ANOTHER tool (e.g. QWIK) on real builds,
                but not yet by us. Treated leniently (like UNCONFIRMED) until our
                own hardware run promotes it to CONFIRMED -- so cross-tool evidence
                never trips the strict path before we verify it.
  UNCONFIRMED - placeholder pending first-hardware confirmation (Appium
                Inspector). UNCONFIRMED locators are exercised leniently so the
                suite stays green in stub mode before Thursday's session.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Any, Dict, Optional, Tuple

CONFIRMED = "CONFIRMED"
CROSS_CONFIRMED = "CROSS_CONFIRMED"
UNCONFIRMED = "UNCONFIRMED"

# Appium/Selenium "by" strategy strings (kept as literals so atak_lib needs no
# Selenium import to be loaded; adapters/real driver accept these directly).
BY_ID = "id"
BY_XPATH = "xpath"
BY_ACCESSIBILITY_ID = "accessibility id"

_SERIES_RE = re.compile(r"\s*(\d+)\.(\d+)")


def normalize_series(version: str) -> str:
    """Reduce a plugin version to its MAJOR.MINOR series for matching.

    ``"3.0.0(859d398a)-[5.7.0]"`` -> ``"3.0"``; ``"3.2.x"`` -> ``"3.2"``. Anything
    without a leading ``N.N`` is returned stripped (so odd values still compare
    equal to themselves). Version overrides key off this series, not the exact
    build, so a 3.2 override applies to any 3.2.x build.
    """
    m = _SERIES_RE.match(str(version))
    return f"{m.group(1)}.{m.group(2)}" if m else str(version).strip()


@dataclass(frozen=True)
class Locator:
    name: str
    by: str
    value: str
    status: str = UNCONFIRMED
    note: str = ""
    # True when this selector was CONFIRMED against an earlier plugin version
    # (e.g. the 2.x legacy audit). `status` always reflects confirmation against
    # the CURRENT target version; provenance is tracked separately so a version
    # bump can demote `status` to UNCONFIRMED without losing the candidate id.
    legacy_confirmed: bool = False
    # Whether this component is expected to be ON the screen for the target
    # release. False => assert it is ABSENT (e.g. removed in an upcoming release).
    expected_present: bool = True
    # Optional expected interactable state, only checked when present. None =
    # don't check; True = must be enabled; False = must be present-but-disabled.
    expect_enabled: Optional[bool] = None
    # Per-version overrides, keyed by MAJOR.MINOR series (e.g. "3.2"). Each value is
    # a dict of fields to override on that version (by/value/status/note/
    # this_build_present/expect_enabled), or {"applies": False} to drop the
    # component on that version. None/empty => identical across all versions (the
    # common case). Excluded from equality/hash so the model stays hashable and two
    # locators compare by their resolved identity.
    versions: Optional[Dict[str, Dict[str, Any]]] = field(default=None, compare=False)

    def as_tuple(self) -> Tuple[str, str]:
        """(by, value) -- the form Appium's find_element expects."""
        return (self.by, self.value)

    def for_version(self, version: Optional[str]) -> Optional["Locator"]:
        """Resolve this locator for a target plugin version.

        Returns self unchanged when there's no version or no matching override (so
        the 3.0-confirmed baseline is never mutated); a new Locator with the
        version's overrides merged on; or None when the override marks the
        component absent from that version (``{"applies": False}``) so the caller
        drops it from the screen's component set.
        """
        if not version or not self.versions:
            return self
        series = normalize_series(version)
        override = next(
            (ov for key, ov in self.versions.items()
             if normalize_series(key) == series),
            None,
        )
        if override is None:
            return self
        if override.get("applies") is False:
            return None
        extra_note = override.get("note")
        return replace(
            self,
            by=str(override.get("by", self.by)),
            value=str(override.get("value", self.value)),
            status=str(override.get("status", self.status)).upper(),
            note=f"{self.note} | [{series}] {extra_note}" if extra_note else self.note,
            expected_present=bool(override["this_build_present"])
            if "this_build_present" in override else self.expected_present,
            expect_enabled=override.get("expect_enabled", self.expect_enabled),
            versions=None,   # resolved -> drop the override map
        )
