"""register_spec_root: consumers add/override screens without forking the lib.

Resolution order is registered roots (newest first), then the specs packaged
inside ``atak_lib.commands``. These tests pin that precedence and the isolation
contract (clear_spec_roots restores the packaged-only baseline).
"""
import pytest

from atak_lib import spec as spec_mod
from atak_lib.spec import (
    clear_spec_roots,
    load_command_spec_by_name,
    register_spec_root,
    spec_roots,
)

_MINIMAL_SPEC = """
name: verify_widget
command: ui.verify_widget
layer: ui
screen_name: widget
assertions:
  - name: title
    by: id
    value: consumer.widget.title
    status: CONFIRMED
"""

_SHADOW_ONBOARDING = """
name: verify_onboarding_screen
command: ui.verify_onboarding_screen
layer: ui
screen_name: onboarding
assertions:
  - name: shadowed_only
    by: id
    value: consumer.override
    status: CONFIRMED
"""


@pytest.fixture(autouse=True)
def _isolate_roots():
    """No registered root may leak between tests."""
    clear_spec_roots()
    yield
    clear_spec_roots()


def _write_spec(root, rel, body):
    f = root / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body)
    return f


def test_no_roots_resolves_packaged_spec():
    # Baseline behavior unchanged: packaged spec still loads with no roots set.
    assert spec_roots() == []
    spec = load_command_spec_by_name("ui.verify_onboarding_screen")
    assert spec.command == "ui.verify_onboarding_screen"


def test_registered_root_supplies_a_new_screen(tmp_path):
    _write_spec(tmp_path, "ui/verify_widget.yaml", _MINIMAL_SPEC)
    register_spec_root(tmp_path)
    spec = load_command_spec_by_name("ui.verify_widget")
    assert spec.command == "ui.verify_widget"
    assert [l.value for l in spec.locators] == ["consumer.widget.title"]


def test_registered_root_shadows_a_packaged_screen(tmp_path):
    _write_spec(tmp_path, "ui/verify_onboarding_screen.yaml", _SHADOW_ONBOARDING)
    register_spec_root(tmp_path)
    spec = load_command_spec_by_name("ui.verify_onboarding_screen")
    assert [l.name for l in spec.locators] == ["shadowed_only"]


def test_newest_root_wins(tmp_path):
    older = tmp_path / "older"
    newer = tmp_path / "newer"
    _write_spec(older, "ui/verify_widget.yaml", _MINIMAL_SPEC)
    _write_spec(newer, "ui/verify_widget.yaml",
                _MINIMAL_SPEC.replace("consumer.widget.title", "newer.win"))
    register_spec_root(older)
    register_spec_root(newer)
    assert spec_roots()[0] == newer.resolve()      # highest priority first
    spec = load_command_spec_by_name("ui.verify_widget")
    assert spec.locators[0].value == "newer.win"


def test_reregister_moves_to_top_priority(tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    _write_spec(a, "ui/verify_widget.yaml",
                _MINIMAL_SPEC.replace("consumer.widget.title", "from.a"))
    _write_spec(b, "ui/verify_widget.yaml",
                _MINIMAL_SPEC.replace("consumer.widget.title", "from.b"))
    register_spec_root(a)
    register_spec_root(b)
    register_spec_root(a)                            # a back on top, no dup
    assert spec_roots() == [a.resolve(), b.resolve()]
    assert load_command_spec_by_name("ui.verify_widget").locators[0].value == "from.a"


def test_clear_spec_roots_restores_packaged_only(tmp_path):
    _write_spec(tmp_path, "ui/verify_onboarding_screen.yaml", _SHADOW_ONBOARDING)
    register_spec_root(tmp_path)
    clear_spec_roots()
    spec = load_command_spec_by_name("ui.verify_onboarding_screen")
    assert "shadowed_only" not in [l.name for l in spec.locators]


def test_register_rejects_non_directory(tmp_path):
    missing = tmp_path / "nope"
    with pytest.raises(ValueError):
        register_spec_root(missing)


def test_unknown_command_names_both_locations(tmp_path):
    register_spec_root(tmp_path)
    with pytest.raises(FileNotFoundError) as ei:
        load_command_spec_by_name("ui.does_not_exist")
    msg = str(ei.value)
    assert str(tmp_path.resolve()) in msg          # registered root named
    assert "atak_lib.commands/ui/does_not_exist.yaml" in msg


def test_module_exposes_extra_roots_list():
    # Internal LIFO list backs the public helpers; sanity that they share state.
    assert spec_mod._EXTRA_ROOTS == []
