"""Version-aware spec support: per-locator version overrides + spec resolution.

Backward compatibility across plugin versions is a hard requirement (older clients
don't always update), so a screen must keep testing the 3.0 baseline while a newer
version (e.g. 3.2) is layered on via overrides -- never by editing the baseline.
These tests pin that resolution logic offline.
"""
import pytest

from atak_lib.spec import CommandSpec, load_command_spec, load_command_spec_by_name
from atak_lib.ui.locators import (
    CONFIRMED,
    UNCONFIRMED,
    Locator,
    normalize_series,
)


def _loc(**kw):
    base = dict(name="relay", by="id", value="base.id", status=CONFIRMED)
    base.update(kw)
    return Locator(**base)


# ---- normalize_series -------------------------------------------------------

@pytest.mark.parametrize("raw,series", [
    ("3.0.0(859d398a)-[5.7.0]", "3.0"),
    ("3.2.x", "3.2"),
    ("3.2", "3.2"),
    ("  3.10.4 ", "3.10"),
    ("nightly", "nightly"),
])
def test_normalize_series(raw, series):
    assert normalize_series(raw) == series


# ---- Locator.for_version ----------------------------------------------------

def test_no_version_or_no_overrides_returns_self():
    base = _loc()
    assert base.for_version(None) is base
    assert base.for_version("3.2") is base          # no `versions` map


def test_non_matching_version_returns_self():
    loc = _loc(versions={"3.2": {"value": "new.id"}})
    assert loc.for_version("3.1") is loc            # 3.1 not in overrides


def test_override_merges_fields_and_matches_by_series():
    loc = _loc(versions={"3.2": {
        "value": "new.id", "status": "UNCONFIRMED", "note": "renamed in 3.2"}})
    out = loc.for_version("3.2.5")                   # series match, not exact
    assert out is not loc
    assert out.value == "new.id"
    assert out.status == UNCONFIRMED
    assert "renamed in 3.2" in out.note
    assert out.versions is None                      # resolved -> overrides dropped
    # baseline untouched
    assert loc.value == "base.id" and loc.status == CONFIRMED


def test_applies_false_drops_component():
    loc = _loc(versions={"3.2": {"applies": False}})
    assert loc.for_version("3.2") is None            # not on the 3.2 screen
    assert loc.for_version("3.0") is loc             # still on 3.0


def test_this_build_present_override():
    loc = _loc(versions={"3.2": {"this_build_present": False}})
    out = loc.for_version("3.2")
    assert out.expected_present is False
    assert loc.expected_present is True              # baseline unchanged


# ---- CommandSpec.for_version ------------------------------------------------

def _spec(locators):
    return CommandSpec(name="s", command="ui.s", layer="ui", screen_name="s",
                       locators=locators, supported_versions=("3.0", "3.2"))


def test_spec_for_version_none_is_identity():
    spec = _spec([_loc()])
    assert spec.for_version(None) is spec


def test_spec_for_version_resolves_and_drops():
    spec = _spec([
        _loc(name="keep"),
        _loc(name="renamed", versions={"3.2": {"value": "v2"}}),
        _loc(name="gone", versions={"3.2": {"applies": False}}),
    ])
    out = spec.for_version("3.2")
    names = [l.name for l in out.locators]
    assert names == ["keep", "renamed"]              # "gone" dropped
    assert next(l for l in out.locators if l.name == "renamed").value == "v2"
    assert out.target_plugin_version == "3.2"
    # 3.0 baseline keeps everything
    base = spec.for_version("3.0")
    assert [l.name for l in base.locators] == ["keep", "renamed", "gone"]


# ---- YAML loader ------------------------------------------------------------

def _write(tmp_path, body):
    p = tmp_path / "ui"
    p.mkdir()
    f = p / "verify_thing.yaml"
    f.write_text(body)
    return f


def test_loader_parses_supported_versions_and_overrides(tmp_path):
    spec = load_command_spec(_write(tmp_path, """
name: verify_thing
command: ui.verify_thing
layer: ui
screen_name: thing
supported_versions: ["3.0", "3.2"]
assertions:
  - name: btn
    by: id
    value: base.id
    status: CONFIRMED
    versions:
      "3.2":
        value: new.id
        status: UNCONFIRMED
"""))
    assert spec.supported_versions == ("3.0", "3.2")
    btn = spec.locators[0]
    assert btn.versions and "3.2" in btn.versions
    resolved = spec.for_version("3.2").locators[0]
    assert resolved.value == "new.id" and resolved.status == UNCONFIRMED


def test_loader_rejects_invalid_override_status(tmp_path):
    with pytest.raises(ValueError):
        load_command_spec(_write(tmp_path, """
name: verify_thing
command: ui.verify_thing
layer: ui
screen_name: thing
assertions:
  - name: btn
    by: id
    value: base.id
    status: CONFIRMED
    versions:
      "3.2": { status: BOGUS }
"""))


# ---- existing specs stay backward-compatible --------------------------------

def test_existing_specs_unchanged_without_version():
    # No version injected -> identical object, today's behavior preserved.
    spec = load_command_spec_by_name("ui.verify_onboarding_screen")
    assert spec.for_version(None) is spec


def test_device_details_declares_supported_versions():
    spec = load_command_spec_by_name("ui.verify_device_details_screen")
    assert spec.supported_versions == ("3.0",)
    # Template override is commented out, so 3.0 and (hypothetical) 3.2 resolve to
    # the same full component set today -- nothing is silently dropped.
    assert len(spec.for_version("3.0").locators) == len(spec.locators)
    assert len(spec.for_version("3.2").locators) == len(spec.locators)
