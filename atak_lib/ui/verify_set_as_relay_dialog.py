"""verify_set_as_relay_dialog -- registers the "Set as Relay" dialog check.

The locators, expected strings, and metadata all live in the YAML spec
(atak_lib/commands/ui/verify_set_as_relay_dialog.yaml) -- the single source of truth. This
module just loads that spec and exposes a thin, registered command function; the
actual soft-assert engine is the shared, OOP :class:`ScreenCommand`. There is no
locator list in this file by design (DRY).

Source of truth: TestRail C149725 "Validate components of Set as Relay dialog"
(Common Functionality Between Apps > Home Page > Device Details; plugin 3.0, ATAK
variant). See the YAML for components and the INTENTIONAL title/body failures
(asserted against the case copy, which the build does not yet match).

Safety: this command asserts only -- it NEVER taps the dialog's confirm "Set as
Relay" button (confirming sets relay mode and disconnects the radio). The navigation
precondition opens the dialog; the test dismisses it via Cancel.

Precondition (not asserted here): a goTenna radio connected via BLE, the plugin on
the Device Details page, and the dialog open (tap
``com.gotenna.atak:id/deviceDetailsRelayModeButton``). See
``atak_lib.ui.navigation.open_set_as_relay_dialog`` / ``cancel_set_as_relay_dialog``.

Stub behaviour: with ``stub=True`` the command returns canned results (the YAML
``stub_returns``) without touching a driver; with ``stub=False`` and a
:class:`StubWebDriver`, the real assertion loop runs offline.
"""
from __future__ import annotations

from typing import List, Optional

from atak_lib.registry import command
from atak_lib.spec import load_command_spec_by_name
from atak_lib.ui.base import ScreenCommand, ScreenVerificationResult

# Loaded once from YAML -- the single source of truth for this dialog.
SPEC = load_command_spec_by_name("ui.verify_set_as_relay_dialog")

# Backwards-compatible module-level views, all sourced from the spec (no
# duplication): tests and adapters can read these without re-listing anything.
SET_AS_RELAY_LOCATORS = SPEC.locators
SCREEN_NAME = SPEC.screen_name
TARGET_PLUGIN_VERSION = SPEC.target_plugin_version
TESTRAIL_CASE_ID = SPEC.testrail_case_id
APPLIES_TO = SPEC.applies_to


@command("ui.verify_set_as_relay_dialog", layer="ui",
         summary="Validate components of the Set as Relay confirm dialog (C149725).")
def verify_set_as_relay_dialog(
    driver,
    *,
    stub: bool = False,
    stub_returns: Optional[List[str]] = None,
    lenient_if_unconfirmed: bool = True,
    plugin_version: Optional[str] = None,
) -> ScreenVerificationResult:
    return ScreenCommand(driver, SPEC, stub=stub,
                         plugin_version=plugin_version).verify(
        stub_returns=stub_returns,
        lenient_if_unconfirmed=lenient_if_unconfirmed,
    )
