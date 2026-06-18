"""Runner-agnostic, ENV-FREE runtime helpers.

The pure pieces any consumer (a test runner, a service, ad-hoc tooling) can use to
drive multi-device runs: device-spec construction from inventory data, and
per-worker device pinning for parallel execution. Importing this package reads no
env vars and touches no files -- the env/stub READ stays in ``adapters/_common``.
"""
from atak_lib.runtime.inventory import device_specs_from_inventory
from atak_lib.runtime.parallel import (
    BASE_SYSTEM_PORT,
    pin_specs,
    worker_index,
)

__all__ = [
    "device_specs_from_inventory",
    "pin_specs",
    "worker_index",
    "BASE_SYSTEM_PORT",
]
