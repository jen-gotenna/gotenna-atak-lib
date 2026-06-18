"""Env-free DeviceSpec construction from already-parsed inventory data.

This is the pure core of device selection: it takes inventory data that someone
ELSE has already loaded, an injected ``stub`` flag, and a ``udid_for`` resolver --
so it reads no env vars and touches no files. The env/stub READ and the
``config/devices.yaml`` file read stay in ``adapters/_common/env.py`` (the only
layer allowed to read env); that wrapper calls this function.
"""
from __future__ import annotations

from typing import Callable, List, Optional

from atak_lib.session.session_manager import DeviceSpec


def device_specs_from_inventory(
    data: dict,
    *,
    stub: bool,
    udid_for: Callable[[int], Optional[str]] = lambda i: None,
    default_count: int = 1,
) -> List[DeviceSpec]:
    """Build DeviceSpecs from already-parsed inventory ``data``. Pure: no env, no
    file I/O.

    ``stub`` and ``udid_for`` are injected by the caller (the adapter resolves
    them from env, e.g. ``stub=stub_mode_enabled()`` and
    ``udid_for=lambda i: os.getenv(f"PHONE{i}")``).

    Stub mode: synthesize placeholder devices (udids irrelevant), honoring the
    inventory's roles/host_variant when present.
    Real mode: each entry's udid is used; if blank, ``udid_for(index)`` fills it.
    Entries with no resolvable udid are skipped. If ``data`` has no entries, fall
    back to a pure ``udid_for(1..n)`` scan (legacy PHONE* convention).
    """
    default_variant = data.get("host_variant", "civ")
    entries = data.get("devices") or []

    if stub:
        if entries:
            return [
                DeviceSpec(
                    udid=(d.get("udid") or f"STUBUDID{i + 1}"),
                    platform_version=str(d.get("platform_version") or "13"),
                    host_variant=d.get("host_variant", default_variant),
                    role=d.get("role", ""),
                )
                for i, d in enumerate(entries)
            ]
        return [DeviceSpec(udid=f"STUBUDID{i + 1}", platform_version="13")
                for i in range(default_count)]

    specs: List[DeviceSpec] = []
    for i, d in enumerate(entries):
        udid = d.get("udid") or udid_for(i + 1)
        if not udid:
            continue
        specs.append(DeviceSpec(
            udid=udid,
            platform_version=str(d.get("platform_version") or "0"),
            host_variant=d.get("host_variant", default_variant),
            role=d.get("role", ""),
        ))

    if not specs:  # legacy fallback: pure udid_for(1..n) scan
        i = 1
        while True:
            udid = udid_for(i)
            if not udid:
                break
            specs.append(DeviceSpec(udid=udid, host_variant=default_variant))
            i += 1

    if not specs:
        raise ValueError(
            "No device udids resolved from the inventory. Pass stub=True for a "
            "hardware-free run, or provide udids (in the inventory or via the "
            "caller's udid resolver)."
        )
    return specs
