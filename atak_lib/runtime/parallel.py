"""Per-worker device pinning for parallel runs (shared by xdist + pabot adapters).

When a candidate runs in parallel, each worker/process must drive a DISTINCT device
on its own UiAutomator2 ``systemPort`` so concurrent sessions on the one Appium
server don't collide. The runner-specific bit (where the worker index comes from)
stays in each adapter:
  * pytest-xdist -> ``PYTEST_XDIST_WORKER`` env var (``gw0``, ``gw1``, ...)
  * pabot        -> ``${PABOTQUEUEINDEX}`` ROBOT VARIABLE (NOT an env var)
Both funnel through :func:`worker_index` + :func:`pin_specs` here so the selection
logic is DRY and unit-testable in stub CI (where the real branch never fires).
"""
from __future__ import annotations

from typing import List, Optional

BASE_SYSTEM_PORT = 8200


def worker_index(raw) -> Optional[int]:
    """Parse a runner worker id to an int, or None.

    Accepts ``'gw3'`` (xdist), ``'2'`` (pabot), ``3`` (int), or None/``'master'``
    (single-process -> None). Anything unparseable -> None.
    """
    if raw is None:
        return None
    s = str(raw)
    if s.startswith("gw"):
        s = s[2:]
    try:
        return int(s)
    except ValueError:
        return None


def pin_specs(specs: List, index: Optional[int],
              base_port: int = BASE_SYSTEM_PORT) -> List:
    """Pin a parallel worker to ONE device + a unique ``systemPort``.

    Returns ``[specs[index % len(specs)]]`` with a ``systemPort`` cap override, or
    ``specs`` unchanged when ``index`` is None or there are <2 devices (so serial /
    single-device / stub runs behave exactly as before). Pure: no env/Appium reads.
    """
    if index is None or len(specs) <= 1:
        return specs
    idx = index % len(specs)
    spec = specs[idx]
    spec.caps_overrides = {**spec.caps_overrides, "systemPort": base_port + idx}
    return [spec]
