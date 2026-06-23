"""register_catalog_root: consumers add/override catalog screens without forking.

Resolution order is registered roots (newest first), then catalogs packaged inside
``atak_lib.selectors``. Mirrors the legacy ``register_spec_root`` contract.
"""
import pytest

from atak_lib.selectors import (
    catalog_roots,
    clear_catalog_roots,
    load_catalog,
    register_catalog_root,
)

_WIDGET = """
screen: widget
layer: ui
selectors:
  title: { by: id, value: consumer.widget.title, status: CONFIRMED }
"""

_SHADOW_ONBOARDING = """
screen: onboarding
layer: ui
selectors:
  shadowed_only: { by: id, value: consumer.override, status: CONFIRMED }
"""


@pytest.fixture(autouse=True)
def _isolate_roots():
    clear_catalog_roots()
    yield
    clear_catalog_roots()


def _write(root, rel, body):
    f = root / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body)
    return f


def test_no_roots_resolves_packaged_catalog():
    assert catalog_roots() == []
    assert load_catalog("ui.onboarding").screen == "onboarding"


def test_registered_root_supplies_a_new_screen(tmp_path):
    _write(tmp_path, "ui/widget.yaml", _WIDGET)
    register_catalog_root(tmp_path)
    cat = load_catalog("ui.widget")
    assert cat.locator("title") == ("id", "consumer.widget.title")


def test_registered_root_shadows_a_packaged_screen(tmp_path):
    _write(tmp_path, "ui/onboarding.yaml", _SHADOW_ONBOARDING)
    register_catalog_root(tmp_path)
    assert list(load_catalog("ui.onboarding").selectors) == ["shadowed_only"]


def test_newest_root_wins(tmp_path):
    older, newer = tmp_path / "older", tmp_path / "newer"
    _write(older, "ui/widget.yaml", _WIDGET)
    _write(newer, "ui/widget.yaml", _WIDGET.replace("consumer.widget.title", "newer.win"))
    register_catalog_root(older)
    register_catalog_root(newer)
    assert catalog_roots()[0] == newer.resolve()
    assert load_catalog("ui.widget").locator("title") == ("id", "newer.win")


def test_reregister_moves_to_top(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    _write(a, "ui/widget.yaml", _WIDGET.replace("consumer.widget.title", "from.a"))
    _write(b, "ui/widget.yaml", _WIDGET.replace("consumer.widget.title", "from.b"))
    register_catalog_root(a)
    register_catalog_root(b)
    register_catalog_root(a)
    assert catalog_roots() == [a.resolve(), b.resolve()]
    assert load_catalog("ui.widget").locator("title") == ("id", "from.a")


def test_clear_restores_packaged_only(tmp_path):
    _write(tmp_path, "ui/onboarding.yaml", _SHADOW_ONBOARDING)
    register_catalog_root(tmp_path)
    clear_catalog_roots()
    assert "shadowed_only" not in load_catalog("ui.onboarding").selectors


def test_register_rejects_non_directory(tmp_path):
    with pytest.raises(ValueError):
        register_catalog_root(tmp_path / "nope")


def test_unknown_screen_names_both_locations(tmp_path):
    register_catalog_root(tmp_path)
    with pytest.raises(FileNotFoundError) as ei:
        load_catalog("ui.does_not_exist")
    msg = str(ei.value)
    assert str(tmp_path.resolve()) in msg
    assert "atak_lib.selectors/ui/does_not_exist.yaml" in msg
