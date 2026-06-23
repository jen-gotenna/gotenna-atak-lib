"""Selector catalog: definitions only, version-aware resolution.

The catalog is the addressable element inventory (QA-3933). It carries selectors +
resolvability, never assertions. These tests pin packaged-catalog loading, by-name
resolution, the unknown-element error, and per-version override resolution.
"""
import pytest

from atak_lib.selectors import (
    Selector,
    load_catalog,
    load_catalog_file,
    locator,
)
from atak_lib.ui.locators import CONFIRMED, UNCONFIRMED


# ---- packaged catalog (onboarding) ------------------------------------------

def test_loads_packaged_onboarding_catalog():
    cat = load_catalog("ui.onboarding")
    assert cat.screen == "onboarding"
    assert cat.app == "com.gotenna.atak"
    assert cat.supported_versions == ("3.0",)
    assert len(cat.selectors) == 10
    assert all(s.status == CONFIRMED for s in cat.selectors.values())


def test_loads_packaged_device_details_catalog():
    cat = load_catalog("ui.device_details")
    assert cat.screen == "device_details"
    assert cat.app == "com.gotenna.atak"
    assert len(cat.selectors) == 23
    assert all(s.status == CONFIRMED for s in cat.selectors.values())
    assert cat.locator("relay_mode_set_button") == (
        "id", "com.gotenna.atak:id/deviceDetailsRelayModeButton")


def test_resolve_id_selector():
    assert locator("ui.onboarding", "login_button") == (
        "id", "com.gotenna.atak:id/loginButton")


def test_resolve_uiautomator_selector_is_passed_through_verbatim():
    by, value = locator("ui.onboarding", "login_subtext")
    assert by == "-android uiautomator"
    assert value.startswith("new UiSelector().resourceId(")


def test_unknown_element_names_available():
    with pytest.raises(KeyError) as ei:
        locator("ui.onboarding", "nope")
    msg = str(ei.value)
    assert "nope" in msg and "login_button" in msg     # lists what's available


# ---- version-aware resolution -----------------------------------------------

def _write(tmp_path, body):
    p = tmp_path / "ui"
    p.mkdir()
    f = p / "thing.yaml"
    f.write_text(body)
    return f


def test_version_override_merges_by_series(tmp_path):
    cat = load_catalog_file(_write(tmp_path, """
screen: thing
layer: ui
supported_versions: ["3.0", "3.2"]
selectors:
  btn:
    by: id
    value: base.id
    status: CONFIRMED
    versions:
      "3.2": { value: new.id, status: UNCONFIRMED }
"""))
    # baseline untouched
    assert cat.locator("btn") == ("id", "base.id")
    assert cat.locator("btn", "3.0") == ("id", "base.id")
    # 3.2.x series matches the "3.2" override (not exact-match)
    assert cat.locator("btn", "3.2.5") == ("id", "new.id")
    assert cat.selectors["btn"].for_version("3.2").status == UNCONFIRMED


def test_applies_false_removes_element_no_stale_locator(tmp_path):
    # Element removed on 3.2: must NOT resolve to the stale baseline locator.
    cat = load_catalog_file(_write(tmp_path, """
screen: thing
layer: ui
supported_versions: ["3.0", "3.2"]
selectors:
  gone:
    by: id
    value: base.id
    status: CONFIRMED
    versions:
      "3.2": { applies: false }
"""))
    # baseline / 3.0: still present
    assert cat.locator("gone", "3.0") == ("id", "base.id")
    assert cat.applies("gone", "3.0") is True
    # 3.2: removed -> for_version is None, applies() False, locator RAISES (no stale tuple)
    assert cat.selectors["gone"].for_version("3.2") is None
    assert cat.applies("gone", "3.2") is False
    with pytest.raises(KeyError) as ei:
        cat.locator("gone", "3.2")
    assert "removed" in str(ei.value) and "base.id" not in str(ei.value)


def test_no_version_returns_baseline():
    s = Selector(name="x", by="id", value="a", status=CONFIRMED)
    assert s.for_version(None) is s
    assert s.for_version("3.2") is s           # no versions map


def test_invalid_status_rejected(tmp_path):
    with pytest.raises(ValueError):
        load_catalog_file(_write(tmp_path, """
screen: thing
selectors:
  btn: { by: id, value: a, status: BOGUS }
"""))


def test_catalog_holds_no_assertion_fields():
    # Guard the driver/oracle boundary: catalog selectors expose locator + resolvability only,
    # never expected-result fields (expect_enabled / this_build_present / present).
    s = load_catalog("ui.onboarding").selectors["login_button"]
    for forbidden in ("expect_enabled", "this_build_present", "expected_present"):
        assert not hasattr(s, forbidden)
