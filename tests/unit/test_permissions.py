from atak_lib.device.permissions import (
    MANAGE_EXTERNAL_STORAGE,
    Permissions,
    core_permissions,
    plugin_permissions,
)
from atak_lib.session.capabilities import ATAK_CORE_PACKAGE


def test_core_permissions_api_gating():
    p11 = core_permissions(11)
    assert "android.permission.BLUETOOTH_CONNECT" not in p11
    assert "android.permission.READ_MEDIA_IMAGES" not in p11
    p12 = core_permissions(12)
    assert "android.permission.BLUETOOTH_SCAN" in p12
    assert "android.permission.READ_MEDIA_IMAGES" not in p12
    p13 = core_permissions(13)
    assert "android.permission.POST_NOTIFICATIONS" in p13
    assert "android.permission.NEARBY_WIFI_DEVICES" in p13
    p14 = core_permissions(14)
    assert "android.permission.READ_MEDIA_VISUAL_USER_SELECTED" in p14


def test_send_sms_only_before_atak_5_5():
    assert "android.permission.SEND_SMS" in core_permissions(13, None)
    assert "android.permission.SEND_SMS" in core_permissions(13, "5.4")
    assert "android.permission.SEND_SMS" not in core_permissions(13, "5.5")
    assert "android.permission.SEND_SMS" not in core_permissions(13, "6.0.1")


def test_plugin_permissions_api_gating():
    assert plugin_permissions(12) == []
    assert plugin_permissions(13) == ["android.permission.POST_NOTIFICATIONS"]


def _recording_runner():
    calls = []

    def runner(argv):
        calls.append(argv)
        return ""
    runner.calls = calls
    return runner


def test_pregrant_core_issues_pm_grant_and_appops():
    r = _recording_runner()
    results = Permissions(runner=r).pregrant_core("UDID", 13, atak_version="5.6")
    # every pm grant uses the right shape
    grants = [c for c in r.calls if c[4:6] == ["pm", "grant"]]
    assert grants, "no pm grant calls"
    assert all(c[:3] == ["adb", "-s", "UDID"] for c in r.calls)
    assert all(c[6] == ATAK_CORE_PACKAGE for c in grants)
    # appops for MANAGE_EXTERNAL_STORAGE
    appops = [c for c in r.calls if "appops" in c]
    assert appops and appops[0][-2:] == [MANAGE_EXTERNAL_STORAGE, "allow"]
    # atak 5.6 -> no SEND_SMS granted
    assert not any(c[-1] == "android.permission.SEND_SMS" for c in grants)
    assert all(ok for _, ok, _ in results)


def test_pregrant_collects_failures_without_raising():
    def runner(argv):
        if argv[-1] == "android.permission.CAMERA":
            raise RuntimeError("denied")
        return ""
    results = Permissions(runner=runner).pregrant(
        "U", "pkg", ["android.permission.CAMERA", "android.permission.RECORD_AUDIO"])
    failed = [perm for perm, ok, _ in results if not ok]
    assert failed == ["android.permission.CAMERA"]
