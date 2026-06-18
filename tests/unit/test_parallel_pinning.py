"""Unit coverage for the parallel per-worker device pinning (crit #6).

The real pinning branch only fires on a multi-device hardware run, so it is inert
in CI -- these tests exercise the pure selection logic offline so a regression in
the index/systemPort derivation is caught without devices.
"""
from atak_lib.runtime.parallel import BASE_SYSTEM_PORT, pin_specs, worker_index
from atak_lib.session.session_manager import DeviceSpec


def _specs(n):
    return [DeviceSpec(udid=f"DEV{i}") for i in range(n)]


# ---- worker_index parsing (xdist 'gwN', pabot 'N', ints, single-process) ----

def test_worker_index_xdist_form():
    assert worker_index("gw0") == 0
    assert worker_index("gw3") == 3


def test_worker_index_pabot_and_int_forms():
    assert worker_index("2") == 2
    assert worker_index(1) == 1


def test_worker_index_single_process_or_garbage_is_none():
    assert worker_index(None) is None
    assert worker_index("master") is None      # not distributed
    assert worker_index("gwX") is None          # unparseable


# ---- pin_specs selection + systemPort + pass-through ----

def test_pin_none_index_passes_through_unchanged():
    specs = _specs(2)
    assert pin_specs(specs, None) is specs


def test_pin_single_device_passes_through_unchanged():
    specs = _specs(1)
    assert pin_specs(specs, 0) is specs         # <2 devices -> no pinning


def test_pin_worker0_selects_device0_with_base_port():
    specs = _specs(2)
    out = pin_specs(specs, 0)
    assert [s.udid for s in out] == ["DEV0"]
    assert out[0].caps_overrides["systemPort"] == BASE_SYSTEM_PORT  # 8200


def test_pin_worker1_selects_device1_with_next_port():
    specs = _specs(2)
    out = pin_specs(specs, 1)
    assert [s.udid for s in out] == ["DEV1"]
    assert out[0].caps_overrides["systemPort"] == BASE_SYSTEM_PORT + 1  # 8201


def test_pin_index_wraps_modulo_device_count():
    specs = _specs(2)
    out = pin_specs(specs, 3)                    # 3 % 2 == 1
    assert [s.udid for s in out] == ["DEV1"]
    assert out[0].caps_overrides["systemPort"] == BASE_SYSTEM_PORT + 1


def test_pin_preserves_existing_caps_overrides():
    specs = [DeviceSpec(udid="DEV0"),
             DeviceSpec(udid="DEV1", caps_overrides={"appWaitDuration": 30000})]
    out = pin_specs(specs, 1)
    assert out[0].caps_overrides["appWaitDuration"] == 30000   # kept
    assert out[0].caps_overrides["systemPort"] == BASE_SYSTEM_PORT + 1  # added


def test_two_workers_get_distinct_devices_and_ports():
    # Simulate gw0 and gw1 each pinning from their own fresh inventory (as the
    # per-process fixtures do) -> distinct device + distinct systemPort, no bleed.
    p0 = pin_specs(_specs(2), worker_index("gw0"))[0]
    p1 = pin_specs(_specs(2), worker_index("gw1"))[0]
    assert p0.udid != p1.udid
    assert p0.caps_overrides["systemPort"] != p1.caps_overrides["systemPort"]
