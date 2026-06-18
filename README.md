# gotenna-atak-lib

Env-agnostic **ATAK UI driver + command library**. Locators and screen checks live
**once** in versioned YAML (the single source of truth); a soft-assert engine runs
them against an Appium driver. Built to be consumed by *any* project — Python test
suites, future QA tooling, or non-Python clients via a service boundary — without
dragging a particular test runner along.

Extracted from the `atak-plugin-v3-qa-automation` suite (QA-3920). One engine, shared
YAML; non-Python consumers reach it through a service rather than re-implementing it.

## Why it's safe to depend on
- **No environment reads.** `atak_lib` never touches env vars; the caller injects the
  stub flag and device udids. Importing it has no side effects beyond loading packaged
  specs.
- **Appium is optional + lazy.** The only hard dependency is PyYAML. Appium is imported
  only when a real session connects (`[appium]` extra).
- **Typed.** Ships `py.typed` (PEP 561).
- **Versioned contract.** The YAML schema + locator-status model is a semver surface —
  see [CHANGELOG.md](CHANGELOG.md).

## Install

```bash
pip install gotenna-atak-lib              # core (PyYAML only)
pip install gotenna-atak-lib[appium]      # + real-device execution
pip install -e ../gotenna-atak-lib        # local dev (editable)
```

## Quickstart

```python
from atak_lib import SessionManager, DeviceSpec, verify_screen

with SessionManager([DeviceSpec(udid="...")], stub=False) as s:
    result = verify_screen("ui.verify_onboarding_screen", s.driver)
    assert result.passed, result.failures
```

Bring your own Appium driver, or let `SessionManager` start one (needs `[appium]`).
For hardware-free runs use `stub=True`.

## Public API

| Symbol | What |
|---|---|
| `SessionManager`, `DeviceSpec` | session lifecycle + device descriptor |
| `verify_screen(name, driver, ...)` | run any spec by dotted name (honors `register_spec_root`) |
| `verify_onboarding_screen` / `verify_device_details_screen` / `verify_set_as_relay_dialog` | the built-in screen checks |
| `register_spec_root(path)` | add/override screens without forking |
| `load_command_spec` / `load_command_spec_by_name` | load a spec (path or dotted name) |
| `CommandSpec`, `ScreenVerificationResult` | the typed result + spec model |
| `catalog` | registered-command catalog: `run` / `available` / `all_specs` / `get` |
| `runtime` | env-free helpers: `device_specs_from_inventory`, `pin_specs`, `worker_index` |

Everything else (`registry`, `ui.base.ScreenCommand`, `session.capabilities`,
`session.stub_driver`) is private and may change without a major bump.

## Add your own screens (no fork, no Python)

```python
from atak_lib import register_spec_root, verify_screen

register_spec_root("my/specs")            # holds ui/verify_foo.yaml (same layout as ours)
verify_screen("ui.verify_foo", driver)    # YAML stays the single source of truth
```

Registered roots are searched **before** packaged specs (newest registration wins), so
you can also shadow a built-in screen.

## The stub contract

`SessionManager([...], stub=True)` runs without hardware: commands return canned
results from each spec's `stub_returns`, and `UNCONFIRMED` locators are tolerated under
the default lenient mode. This keeps a consumer's suite green before locators are
hardware-confirmed.

## Versioning across app releases

Specs carry `supported_versions` and per-locator `versions` overrides; `verify_screen`
and `CommandSpec.for_version(v)` resolve the right locators for a given plugin version
so older-version coverage isn't broken when the app changes. Full model + recipe:
`docs/legacy_versioning.md` (framework repo).

## Development

```bash
pip install -e .[dev]
pytest                      # runs tests/unit
```

The unit suite is the library's contract — it travels with this repo.
