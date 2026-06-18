from atak_lib.session.capabilities import (
    ATAK_CORE_ACTIVITY,
    ATAK_CORE_PACKAGE,
    build_capabilities,
)


def test_capabilities_match_confirmed_legacy_profile():
    caps = build_capabilities("RF8M20YD00W", "13")
    assert caps["appPackage"] == ATAK_CORE_PACKAGE == "com.atakmap.app.civ"
    assert caps["appActivity"] == ATAK_CORE_ACTIVITY == "com.atakmap.app.ATAKActivityCiv"
    assert caps["automationName"] == "UiAutomator2"
    assert caps["noReset"] is True
    assert caps["platformVersion"] == "13"
    assert caps["udid"] == "RF8M20YD00W"


def test_capabilities_overrides():
    caps = build_capabilities("X", "12", newCommandTimeout=60)
    assert caps["newCommandTimeout"] == 60


def test_host_variant_civ_is_default_and_confirmed():
    from atak_lib.session.capabilities import HOST_PROFILES, build_capabilities
    caps = build_capabilities("U", "13")
    assert caps["appPackage"] == "com.atakmap.app.civ"
    assert caps["appActivity"] == "com.atakmap.app.ATAKActivityCiv"
    assert HOST_PROFILES["civ"]["confirmed"] is True


def test_host_variant_mil_profile_is_placeholder():
    from atak_lib.session.capabilities import HOST_PROFILES, build_capabilities
    caps = build_capabilities("U", "13", "mil")
    assert caps["appPackage"] == HOST_PROFILES["mil"]["package"]
    # MilTAK package/activity are NOT yet confirmed.
    assert HOST_PROFILES["mil"]["confirmed"] is False


def test_unknown_host_variant_raises():
    import pytest
    from atak_lib.session.capabilities import build_capabilities
    with pytest.raises(ValueError):
        build_capabilities("U", "13", "winTAK")
