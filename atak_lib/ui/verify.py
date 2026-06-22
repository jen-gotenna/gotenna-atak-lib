"""Generic, declarative screen verification.

``verify_screen`` resolves a command spec by dotted name -- honoring any
``register_spec_root`` overrides -- and runs the shared soft-assert engine against
it. The engine (:class:`~atak_lib.ui.base.ScreenCommand`) stays internal.

LEGACY (RFC 0001): this is the *library-asserts* path -- it bundles the expected
results into the library. Under the driver/oracle split the library reports facts and
the **consumer** owns assertions. Prefer :class:`atak_lib.Screen` (selectors +
manipulation + state queries) plus your own assertions; see
``docs/migration-verify-to-screen.md`` and ``examples/consumer_oracle.py``. The
``verify_*`` path still works and is unchanged, but is slated for removal in a future
major once consumers have migrated.
"""
from __future__ import annotations

from typing import List, Optional

from atak_lib.spec import load_command_spec_by_name
from atak_lib.ui.base import ScreenCommand, ScreenVerificationResult


def verify_screen(
    command_name: str,
    driver,
    *,
    stub: bool = False,
    plugin_version: Optional[str] = None,
    stub_returns: Optional[List[str]] = None,
    lenient_if_unconfirmed: bool = True,
) -> ScreenVerificationResult:
    """Resolve ``command_name``'s spec (registered roots first, then packaged) and
    run the soft-assert engine against ``driver``.

    Mirrors the dedicated ``verify_*`` wrappers but works for ANY spec name,
    including consumer-registered screens, with no bespoke Python per screen.
    """
    spec = load_command_spec_by_name(command_name)
    return ScreenCommand(driver, spec, stub=stub,
                         plugin_version=plugin_version).verify(
        stub_returns=stub_returns,
        lenient_if_unconfirmed=lenient_if_unconfirmed,
    )
