from atak_lib.device.adb import ADB
from atak_lib.radio.bluetooth import Bluetooth


def make_runner(responses):
    calls = []

    def runner(argv):
        calls.append(argv)
        for key, out in responses.items():
            if key in " ".join(argv):
                return out
        return ""
    runner.calls = calls
    return runner


def test_get_os_version():
    adb = ADB(runner=make_runner({"ro.build.version.release": "13\n"}))
    assert adb.get_os_version("UDID") == "13"


def test_get_plugin_version_regex():
    out = "  versionName=2.3.1\n  versionCode=4011\n"
    adb = ADB(runner=make_runner({"com.gotenna.atak": out}))
    assert adb.get_plugin_version("UDID") == "2.3.1"


def test_get_versions_playstore_detection():
    core = "versionName=5.2.0 playstore flavor"
    plugin = "versionName=2.3.1 versionCode=4011"

    def runner(argv):
        j = " ".join(argv)
        if "com.atakmap.app.civ" in j:
            return core
        if "com.gotenna.atak" in j:
            return plugin
        return ""
    v = ADB(runner=runner).get_versions("UDID")
    assert v["core_version"] == "5.2.0"
    assert v["build_type"] == "Playstore"
    assert v["plugin_version"] == "2.3.1"
    assert v["build_number"] == "4011"


def test_is_app_crashed():
    assert ADB(runner=lambda a: "system_server\n").is_app_crashed("UDID") is True
    assert ADB(runner=lambda a: "com.atakmap.app.civ\n").is_app_crashed("UDID") is False


def test_ble_status_on_off_unknown():
    bt_on = Bluetooth(runner=lambda a: "  enabled: true\n")
    bt_off = Bluetooth(runner=lambda a: "  enabled: false\n")
    bt_unk = Bluetooth(runner=lambda a: "nothing here\n")
    assert bt_on.get_BLE_status("U")[0] == "on"
    assert bt_off.get_BLE_status("U")[0] == "off"
    assert bt_unk.get_BLE_status("U")[0] == "unknown"
    assert bt_on.verify_BLE_on("U")[0] is True
    assert bt_off.verify_BLE_off("U")[0] is True


def test_bluetooth_enable_disable_invoke_runner():
    r = make_runner({})
    bt = Bluetooth(runner=r)
    bt.enable_bluetooth("U")
    bt.disable_bluetooth("U")
    assert ["adb", "-s", "U", "shell", "svc", "bluetooth", "enable"] in r.calls
    assert ["adb", "-s", "U", "shell", "svc", "bluetooth", "disable"] in r.calls
