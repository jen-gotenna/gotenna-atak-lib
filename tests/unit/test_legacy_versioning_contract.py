"""Contract: the version-aware machinery holds for the SHIPPED specs.

Backward compatibility across plugin versions is a hard requirement -- older
clients don't always update, so a screen must keep resolving its baseline while
newer versions are layered on via per-locator overrides (never by editing the
baseline). The unit-level resolution logic is pinned in
``test_version_aware_specs.py``; this module guards the *distributed* specs so a
future edit can't ship a spec whose declared versions silently fail to resolve.

No loader/resolver behavior is asserted here beyond what already exists -- this is
a regression net over real data, not a new rule on the engine.
"""
import pytest

from atak_lib import catalog
from atak_lib.spec import load_command_spec_by_name
from atak_lib.ui.locators import normalize_series

# Every UI command that ships in the wheel, by dotted name.
_SHIPPED = [s.name for s in catalog.all_specs()]


def _specs():
    return [(name, load_command_spec_by_name(name)) for name in _SHIPPED]


def test_there_are_shipped_specs():
    # Guard the guard: if discovery breaks, the parametrized tests would vacuously
    # pass. Make that loud instead.
    assert _SHIPPED, "no commands registered via catalog"


@pytest.mark.parametrize("name,spec", _specs(), ids=_SHIPPED)
def test_each_supported_version_resolves_to_a_nonempty_screen(name, spec):
    versions = spec.supported_versions or ((spec.target_plugin_version,)
                                           if spec.target_plugin_version else ())
    for v in versions:
        resolved = spec.for_version(v)
        assert resolved.locators, (
            f"{name} resolves to ZERO components for supported version {v!r} -- "
            f"an override likely drops the whole screen")


@pytest.mark.parametrize("name,spec", _specs(), ids=_SHIPPED)
def test_baseline_version_is_in_supported_versions(name, spec):
    if not spec.supported_versions or not spec.target_plugin_version:
        pytest.skip("single-version spec (no supported_versions declared)")
    baseline = normalize_series(spec.target_plugin_version)
    supported = {normalize_series(v) for v in spec.supported_versions}
    assert baseline in supported, (
        f"{name} baselines {baseline!r} but supported_versions={sorted(supported)} "
        f"-- the baseline version must be one the screen claims to support")


@pytest.mark.parametrize("name,spec", _specs(), ids=_SHIPPED)
def test_per_locator_overrides_target_a_supported_version(name, spec):
    if not spec.supported_versions:
        pytest.skip("single-version spec (overrides resolve only on demand)")
    supported = {normalize_series(v) for v in spec.supported_versions}
    for loc in spec.locators:
        for key in (loc.versions or {}):
            series = normalize_series(key)
            assert series in supported, (
                f"{name}: locator {loc.name!r} has a {key!r} override but that "
                f"series is not in supported_versions={sorted(supported)} -- it "
                f"would be dead config under version-driven runs")
