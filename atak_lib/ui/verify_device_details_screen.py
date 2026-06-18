"""verify_device_details_screen -- registers the radio Device Details check.

The locators, expected strings, and metadata all live in the YAML spec
(atak_lib/commands/ui/verify_device_details_screen.yaml) -- the single source of truth.
This module just loads that spec and exposes a thin, registered command function;
the actual soft-assert engine is the shared, OOP :class:`ScreenCommand`. There is
no locator list in this file by design (DRY).

Source of truth: TestRail C149719 "Validate Device Details page components when
connected to a radio via BLE" (Common Functionality Between Apps; plugin 3.0,
ATAK variant). See the YAML for components, dynamic-value notes, the Pro-App-scoped
PRO-* exclusions (which do NOT apply to the plugin), and known gaps.

Precondition (not asserted here): a goTenna radio connected via BLE, and the
plugin on the Device Details page (tap the device card on the radio status
screen). Connecting a radio advances the plugin past the onboarding home screen.

Stub behaviour: with ``stub=True`` the command returns canned results (the YAML
``stub_returns``) without touching a driver. With ``stub=False`` and a
:class:`StubWebDriver`, the real assertion loop runs offline.
"""
from __future__ import annotations

from typing import List, Optional

from atak_lib.registry import command
from atak_lib.spec import load_command_spec_by_name
from atak_lib.ui.base import ScreenCommand, ScreenVerificationResult

# Loaded once from YAML -- the single source of truth for this screen.
SPEC = load_command_spec_by_name("ui.verify_device_details_screen")

# Backwards-compatible module-level views, all sourced from the spec (no
# duplication): tests and adapters can read these without re-listing anything.
DEVICE_DETAILS_LOCATORS = SPEC.locators
SCREEN_NAME = SPEC.screen_name
TARGET_PLUGIN_VERSION = SPEC.target_plugin_version
TESTRAIL_CASE_ID = SPEC.testrail_case_id
APPLIES_TO = SPEC.applies_to


@command("ui.verify_device_details_screen", layer="ui",
         summary="Validate components of the radio Device Details page (C149719).")
def verify_device_details_screen(
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
