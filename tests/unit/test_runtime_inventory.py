"""The runtime inventory core is PURE: no env reads, no file I/O.

device_specs_from_env (adapters) is the env boundary and is covered by
tests/unit/test_device_inventory.py. Here we pin the env-free core directly --
data + stub + udid_for are injected, so these tests pass no matter what env vars
are set -- and assert that importing atak_lib.runtime triggers no env read.
"""
import pytest

from atak_lib.runtime import device_specs_from_inventory


def test_stub_with_entries_honors_roles_without_env():
    data = {"host_variant": "civ",
            "devices": [{"role": "GT1"}, {"role": "GT2"}]}
    specs = device_specs_from_inventory(data, stub=True)
    assert [s.role for s in specs] == ["GT1", "GT2"]
    assert all(s.host_variant == "civ" for s in specs)
    assert all(s.udid.startswith("STUBUDID") for s in specs)


def test_stub_without_entries_uses_default_count():
    specs = device_specs_from_inventory({}, stub=True, default_count=3)
    assert [s.udid for s in specs] == ["STUBUDID1", "STUBUDID2", "STUBUDID3"]


def test_real_uses_inventory_udid_and_per_device_variant():
    data = {"host_variant": "civ",
            "devices": [{"role": "GT1", "udid": "RF8M20YD00W",
                         "host_variant": "mil"}]}
    specs = device_specs_from_inventory(data, stub=False)
    assert len(specs) == 1
    assert specs[0].udid == "RF8M20YD00W"
    assert specs[0].host_variant == "mil"     # per-device override
    assert specs[0].role == "GT1"


def test_real_blank_udid_filled_by_injected_resolver():
    data = {"devices": [{"role": "GT1", "udid": ""}]}
    specs = device_specs_from_inventory(
        data, stub=False, udid_for=lambda i: {1: "INJECTED1"}.get(i))
    assert specs[0].udid == "INJECTED1"


def test_real_legacy_scan_when_no_entries():
    pool = {1: "A", 2: "B"}
    specs = device_specs_from_inventory(
        {}, stub=False, udid_for=lambda i: pool.get(i))
    assert [s.udid for s in specs] == ["A", "B"]


def test_real_no_udids_raises():
    with pytest.raises(ValueError):
        device_specs_from_inventory({"devices": []}, stub=False)


def test_default_resolver_returns_no_devices_in_real_mode():
    # The default udid_for resolves nothing, so a real run with no inventory
    # udids raises -- proving the core never reaches out to env on its own.
    with pytest.raises(ValueError):
        device_specs_from_inventory({"devices": [{"role": "GT1"}]}, stub=False)


def test_import_runtime_is_env_free(monkeypatch):
    # Importing the runtime package (and its submodules) must read no env. Trip
    # every env access path and reload to prove it stays clean.
    import importlib

    import atak_lib.runtime
    import atak_lib.runtime.inventory
    import atak_lib.runtime.parallel

    def _boom(*a, **k):                      # pragma: no cover - must not fire
        raise AssertionError("atak_lib.runtime read env at import time")

    monkeypatch.setattr("os.getenv", _boom)
    monkeypatch.setattr("os.environ.get", _boom)

    for mod in (atak_lib.runtime.parallel,
                atak_lib.runtime.inventory,
                atak_lib.runtime):
        importlib.reload(mod)
    assert hasattr(atak_lib.runtime, "device_specs_from_inventory")
