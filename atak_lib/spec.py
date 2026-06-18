"""Command-spec loader -- YAML is the single source of truth.

A command spec (atak_lib/commands/<layer>/<name>.yaml) defines a command's metadata and
its locator/assertion set ONCE. This module parses that YAML into typed objects
(:class:`CommandSpec` + :class:`Locator`) so the implementation never re-lists
locators in Python. DRY: edit the YAML, every runner sees the change.

Pure Python: reads a data file, no env, no framework, no Appium. PyYAML is a core
dependency of the suite.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from importlib import resources
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from atak_lib.ui.locators import (
    CONFIRMED,
    CROSS_CONFIRMED,
    UNCONFIRMED,
    Locator,
    normalize_series,
)

# Specs ship INSIDE the package (atak_lib/commands/) so a pip-installed wheel
# finds them. Resolution goes through importlib.resources, which works from a
# source tree, an installed wheel, or a zipapp. COMMANDS_DIR is kept as a
# back-compat traversable for callers/tests that walk the spec tree directly.
_COMMANDS_PKG = "atak_lib.commands"
COMMANDS_DIR = resources.files(_COMMANDS_PKG)

_VALID_STATUS = {CONFIRMED, CROSS_CONFIRMED, UNCONFIRMED}


@dataclass(frozen=True)
class CommandSpec:
    name: str
    command: str                 # dotted registry name, e.g. ui.verify_onboarding_screen
    layer: str
    screen_name: str
    locators: List[Locator]
    stub_failures: List[str] = field(default_factory=list)
    scrollable: bool = False     # long screen -> verifier scrolls locators into view
    target_plugin_version: str = ""
    testrail_case_id: str = ""
    applies_to: tuple = ()
    source_path: Optional[Path] = None
    # Plugin version series this screen is maintained for (e.g. ("3.0", "3.2")).
    # Empty => single-version (the target_plugin_version baseline). Backward-compat
    # is preserved by adding a series here + per-locator `versions` overrides,
    # never by editing the baseline locators.
    supported_versions: tuple = ()

    def for_version(self, version: Optional[str]) -> "CommandSpec":
        """Return a spec view resolved for a target plugin version.

        Applies each locator's version override and drops components that don't
        apply to that version. ``for_version(None)`` returns the spec unchanged --
        so existing single-version callers behave exactly as before.
        """
        if not version:
            return self
        resolved = [
            lv for lv in (l.for_version(version) for l in self.locators)
            if lv is not None
        ]
        return replace(self, locators=resolved,
                       target_plugin_version=normalize_series(version))


def _build_versions(a: Dict[str, Any]) -> Optional[Dict[str, Dict[str, Any]]]:
    """Parse + validate a locator's optional per-version override map."""
    raw = a.get("versions")
    if not raw:
        return None
    if not isinstance(raw, dict):
        raise ValueError(f"Locator '{a.get('name')}' versions must be a mapping")
    out: Dict[str, Dict[str, Any]] = {}
    for ver, ov in raw.items():
        if not isinstance(ov, dict):
            raise ValueError(
                f"Locator '{a.get('name')}' version {ver!r} override must be a mapping")
        if "status" in ov:
            st = str(ov["status"]).upper()
            if st not in _VALID_STATUS:
                raise ValueError(
                    f"Locator '{a.get('name')}' version {ver!r} has invalid "
                    f"status {st!r}")
            ov = {**ov, "status": st}
        out[str(ver)] = ov
    return out


def _build_locator(a: Dict[str, Any]) -> Locator:
    status = str(a.get("status", UNCONFIRMED)).upper()
    if status not in _VALID_STATUS:
        raise ValueError(f"Locator '{a.get('name')}' has invalid status {status!r}")
    # Compose a human note from the spec's component/note/todo fields.
    note = " | ".join(
        str(a[k]) for k in ("component", "note", "todo") if a.get(k)
    )
    return Locator(
        name=a["name"],
        by=str(a["by"]),
        value=str(a["value"]),
        status=status,
        note=note,
        legacy_confirmed=bool(a.get("legacy_confirmed", False)),
        # YAML uses this_build_present (build-gating); default present.
        expected_present=bool(a.get("this_build_present", True)),
        expect_enabled=a.get("expect_enabled", None),
        versions=_build_versions(a),
    )


def load_command_spec(path: Path | str) -> CommandSpec:
    path = Path(path)
    data = yaml.safe_load(path.read_text())

    assertions = data.get("assertions") or []
    locators = [_build_locator(a) for a in assertions]

    stub = (data.get("stub_returns") or {}).get("failures") or []
    testrail = data.get("testrail") or {}

    return CommandSpec(
        name=data["name"],
        command=data.get("command", f"{data.get('layer', 'ui')}.{data['name']}"),
        layer=data.get("layer", "ui"),
        screen_name=data.get("screen_name", data["name"]),
        locators=locators,
        stub_failures=list(stub),
        scrollable=bool(data.get("scrollable", False)),
        target_plugin_version=str(data.get("target_plugin_version", "")),
        testrail_case_id=str(testrail.get("case_id", "")),
        applies_to=tuple(testrail.get("applies_to", ()) or ()),
        source_path=path,
        supported_versions=tuple(data.get("supported_versions", ()) or ()),
    )


# Consumer-registered spec roots, searched BEFORE the packaged specs (LIFO: a
# later registration shadows earlier ones and the packaged baseline). Lets a
# consuming project add or override screens without forking the library.
_EXTRA_ROOTS: List[Path] = []


def register_spec_root(path: Path | str) -> None:
    """Register a consumer-owned spec directory, searched before packaged specs.

    A registered root mirrors the packaged layout (``<root>/<layer>/<name>.yaml``).
    Most-recently registered wins, so a consumer can shadow a packaged screen.
    Idempotent: re-registering the same dir moves it to highest priority.
    """
    p = Path(path)
    if not p.is_dir():
        raise ValueError(f"spec root is not a directory: {p}")
    p = p.resolve()
    if p in _EXTRA_ROOTS:
        _EXTRA_ROOTS.remove(p)
    _EXTRA_ROOTS.append(p)


def clear_spec_roots() -> None:
    """Drop all consumer-registered spec roots (back to packaged specs only)."""
    _EXTRA_ROOTS.clear()


def spec_roots() -> List[Path]:
    """Registered roots, highest priority first."""
    return list(reversed(_EXTRA_ROOTS))


def load_command_spec_by_name(command: str) -> CommandSpec:
    """Load by dotted name, e.g. 'ui.verify_onboarding_screen'.

    Resolution order: consumer-registered roots (newest first), then the specs
    packaged inside ``atak_lib.commands``.
    """
    layer, _, name = command.partition(".")
    rel = Path(layer) / f"{name}.yaml"
    for root in reversed(_EXTRA_ROOTS):
        cand = root / rel
        if cand.is_file():
            return load_command_spec(cand)
    ref = resources.files(_COMMANDS_PKG) / layer / f"{name}.yaml"
    if not ref.is_file():
        searched = ", ".join(str(r) for r in reversed(_EXTRA_ROOTS)) or "(none)"
        raise FileNotFoundError(
            f"No spec for command '{command}'. Searched registered roots "
            f"[{searched}] then packaged atak_lib.commands/{layer}/{name}.yaml.")
    with resources.as_file(ref) as path:   # real fs path even from a wheel/zip
        return load_command_spec(path)
