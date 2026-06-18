"""The YAML spec is the single source of truth; verify the loader honors it."""
import yaml

from atak_lib.spec import (
    COMMANDS_DIR,
    load_command_spec,
    load_command_spec_by_name,
)
from atak_lib.ui.locators import UNCONFIRMED

SPEC_PATH = COMMANDS_DIR / "ui" / "verify_onboarding_screen.yaml"


def test_loads_by_name_and_by_path_equivalently():
    a = load_command_spec_by_name("ui.verify_onboarding_screen")
    b = load_command_spec(SPEC_PATH)
    assert a.command == b.command == "ui.verify_onboarding_screen"
    assert [l.name for l in a.locators] == [l.name for l in b.locators]


def test_locators_match_yaml_exactly_no_python_duplication():
    raw = yaml.safe_load(SPEC_PATH.read_text())
    spec = load_command_spec(SPEC_PATH)
    yaml_names = [a["name"] for a in raw["assertions"]]
    assert [l.name for l in spec.locators] == yaml_names
    by_name = {l.name: l for l in spec.locators}
    for a in raw["assertions"]:
        loc = by_name[a["name"]]
        assert loc.by == str(a["by"])
        assert loc.value == str(a["value"])
        assert loc.status == str(a.get("status", UNCONFIRMED)).upper()
        # this_build_present -> expected_present
        assert loc.expected_present == bool(a.get("this_build_present", True))
        assert loc.expect_enabled == a.get("expect_enabled", None)


def test_atak_plugin_has_no_gated_components():
    # On the ATAK plugin all components are present; the Pro-App-scoped absences
    # (PRO-318/PRO-330) live in the proapp sample, not the plugin spec.
    raw = yaml.safe_load(SPEC_PATH.read_text())
    gated = {a["name"] for a in raw["assertions"]
             if a.get("this_build_present") is False}
    assert gated == set()


def test_proapp_sample_gates_the_pro_absences():
    sample = (COMMANDS_DIR / "ui" / "samples"
              / "verify_onboarding_screen.proapp.sample.yaml")
    raw = yaml.safe_load(sample.read_text())
    gated = {a["name"] for a in raw["assertions"]
             if a.get("this_build_present") is False}
    assert gated == {
        "logo_subtext", "deploy_qr_button", "deploy_qr_subtext",
        "manual_setup_button", "manual_setup_subtext",
    }


def test_metadata_from_yaml():
    spec = load_command_spec(SPEC_PATH)
    assert spec.testrail_case_id == "C147673"
    assert spec.target_plugin_version == "3.0"
    applies = {a.lower() for a in spec.applies_to}
    assert "atak" in applies and "pro" in applies
