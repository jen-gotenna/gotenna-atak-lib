"""Selector catalog -- the addressable element inventory (definitions only).

The catalog answers a single question: *how do I address element X on screen Y
(for app version V)?* It holds **no assertions / expected results** -- those belong
to each consuming test framework (QA-3933, docs/design/shared-ui-driver.md). What
lives here is the locator (`by`/`value`) and its **resolvability** (`status`,
`legacy_confirmed`, per-version overrides) -- the property that decides which
selector is valid on a given build.

Selectors ship as YAML inside the package and load via importlib.resources.
Version-awareness reuses the same MAJOR.MINOR series matching as the locator model.

Reserved (QA-3933 decision 5): a per-target override axis for non-Android targets
(a Flutter app addressed by semantic label, iOS, web). Additive; not resolved yet.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from importlib import resources
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml

from atak_lib.ui.locators import (
    CONFIRMED,
    CROSS_CONFIRMED,
    UNCONFIRMED,
    normalize_series,
)

_CATALOG_PKG = "atak_lib.selectors"
_VALID_STATUS = {CONFIRMED, CROSS_CONFIRMED, UNCONFIRMED}


@dataclass(frozen=True)
class Selector:
    """One addressable element: a locator + its resolvability metadata."""
    name: str
    by: str
    value: str
    status: str = UNCONFIRMED
    description: str = ""
    legacy_confirmed: bool = False
    # Per-version overrides keyed by MAJOR.MINOR series (by/value/status). Excluded
    # from equality so two selectors compare by resolved identity.
    versions: Optional[Dict[str, Dict[str, Any]]] = field(default=None, compare=False)

    def as_tuple(self) -> Tuple[str, str]:
        """(by, value) -- the form Appium's find_element expects."""
        return (self.by, self.value)

    def for_version(self, version: Optional[str]) -> Optional["Selector"]:
        """Resolve this selector for a target app version.

        Returns self unchanged when there's no version or no matching override (the
        baseline is never mutated); a new Selector with the version's by/value/status
        merged on; or **None** when the override marks the element absent on that
        version (``{"applies": false}``) -- the element was removed/renamed away in
        that build, so there is no valid selector. (Parity with
        :meth:`atak_lib.ui.locators.Locator.for_version`; not returning the stale
        baseline is the backward-compat contract.)
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
            return None          # element removed on this version -- no selector
        status = str(override.get("status", self.status)).upper()
        if status not in _VALID_STATUS:
            raise ValueError(
                f"selector {self.name!r} version {series} has invalid status {status!r}")
        return replace(
            self,
            by=str(override.get("by", self.by)),
            value=str(override.get("value", self.value)),
            status=status,
            versions=None,   # resolved -> drop the override map
        )


@dataclass(frozen=True)
class SelectorCatalog:
    """All selectors for one screen, version-aware."""
    screen: str
    layer: str
    selectors: Dict[str, Selector]
    app: str = ""
    supported_versions: tuple = ()

    def applies(self, element: str, version: Optional[str] = None) -> bool:
        """Whether ``element`` exists on ``version`` (False if removed via an
        ``applies: false`` override). Lets a consumer check applicability without
        catching the removed-element error from :meth:`locator`."""
        return self.selectors[element].for_version(version) is not None

    def locator(self, element: str, version: Optional[str] = None) -> Tuple[str, str]:
        """Resolve ``(by, value)`` for ``element`` (version-aware).

        Raises ``KeyError`` if the element is unknown, or if it is **removed** on the
        requested version (``applies: false``) -- never returns a stale baseline
        locator for an element that doesn't exist on that build. Check
        :meth:`applies` first if a missing element is expected.
        """
        try:
            sel = self.selectors[element]
        except KeyError:
            raise KeyError(
                f"no selector {element!r} on screen {self.screen!r}; have: "
                f"{', '.join(sorted(self.selectors)) or '(none)'}")
        resolved = sel.for_version(version)
        if resolved is None:
            raise KeyError(
                f"selector {element!r} is removed on version {version!r} "
                f"(applies: false) on screen {self.screen!r} -- no valid selector")
        return resolved.as_tuple()


def _build_selector(name: str, d: Dict[str, Any]) -> Selector:
    status = str(d.get("status", UNCONFIRMED)).upper()
    if status not in _VALID_STATUS:
        raise ValueError(f"selector {name!r} has invalid status {status!r}")
    return Selector(
        name=name,
        by=str(d["by"]),
        value=str(d["value"]),
        status=status,
        description=str(d.get("description", "")),
        legacy_confirmed=bool(d.get("legacy_confirmed", False)),
        versions=d.get("versions") or None,
    )


def load_catalog_file(path: Path | str) -> SelectorCatalog:
    """Load a selector catalog from an explicit YAML path (external/ad-hoc)."""
    data = yaml.safe_load(Path(path).read_text()) or {}
    selectors = {
        name: _build_selector(name, sd)
        for name, sd in (data.get("selectors") or {}).items()
    }
    return SelectorCatalog(
        screen=data["screen"],
        layer=data.get("layer", "ui"),
        selectors=selectors,
        app=str(data.get("app", "")),
        supported_versions=tuple(data.get("supported_versions", ()) or ()),
    )


def load_catalog(screen: str) -> SelectorCatalog:
    """Load a packaged catalog by dotted name, e.g. ``'ui.onboarding'``."""
    layer, _, name = screen.partition(".")
    ref = resources.files(_CATALOG_PKG) / layer / f"{name}.yaml"
    with resources.as_file(ref) as path:   # real fs path even from a wheel/zip
        return load_catalog_file(path)


def locator(screen: str, element: str, version: Optional[str] = None) -> Tuple[str, str]:
    """Resolve ``(by, value)`` for ``element`` on ``screen`` (version-aware)."""
    return load_catalog(screen).locator(element, version)
