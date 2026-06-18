"""Command catalog -- imports every command module so the registry is populated.

Import this (instead of individual command modules) when a runner needs the full
set of commands available by name. Add new command modules here as they land.
"""
from __future__ import annotations

# Importing a command module triggers its @command registration side effects.
from atak_lib.ui import verify_onboarding_screen as _verify_onboarding_screen  # noqa: F401
from atak_lib.ui import verify_device_details_screen as _verify_device_details_screen  # noqa: F401
from atak_lib.ui import verify_set_as_relay_dialog as _verify_set_as_relay_dialog  # noqa: F401

from atak_lib.registry import all_specs, available, get, run  # noqa: F401

__all__ = ["all_specs", "available", "get", "run"]
