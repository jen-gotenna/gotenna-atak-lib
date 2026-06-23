# gotenna-atak-lib

Env-agnostic **shared UI driver** for the goTenna ATAK plugin. Selectors live **once**
in versioned YAML (the single source of truth); a `Screen` facade resolves them and
drives an Appium driver. The library **reports facts** (is this element present /
enabled / what's its text) — **your test framework owns the expected-result
assertions**. Built to be consumed by *any* project: Python suites by import,
non-Python clients (QWIK, other apps) via an HTTP service boundary.

Extracted from `atak-plugin-v3-qa-automation` (QA-3920); evolved into a shared driver
under QA-3933. One engine, one YAML source of truth; no consumer redefines selectors.

## Why it's safe to depend on
- **Driver, not oracle.** The library finds/queries/drives; it never asserts pass/fail.
  Each consumer applies its own expectations against the facts it returns.
- **No environment reads.** `atak_lib` never touches env vars; the caller injects the
  stub flag and device udids. Importing it loads no env and no Appium.
- **Appium is optional + lazy.** Only hard dependency is PyYAML; Appium imports only
  when a real session connects (`[appium]` extra).
- **Typed** (`py.typed`, PEP 561). **Versioned contract** — the YAML selector schema is
  a semver surface; see [CHANGELOG.md](CHANGELOG.md).

## Install

```bash
pip install gotenna-atak-lib              # core (PyYAML only)
pip install gotenna-atak-lib[appium]      # + real-device execution (Appium/Selenium)
pip install gotenna-atak-lib[server]      # + the HTTP service boundary (stdlib today)
pip install -e ../gotenna-atak-lib        # local dev (editable)
```

## Quickstart — drive + assert (the consumer pattern)

```python
from atak_lib import SessionManager, DeviceSpec, Screen

with SessionManager([DeviceSpec(udid="...")], stub=False) as s:
    screen = Screen("ui.onboarding", s.driver)        # version=... for a specific build
    screen.tap("login_button")                        # manipulation
    # YOUR expectations live in YOUR repo — the library only reports facts:
    assert screen.is_present("terms_of_service_checkbox")
    assert screen.is_enabled("login_button")
    assert screen.get_text("logo_subtext") == "Please select a deployment option below"
```

`Screen` methods: `tap`, `type`, `wait_for`, `scroll_into_view` (manipulation) and
`is_present`, `is_enabled`, `get_text` (facts). Bring your own Appium driver or let
`SessionManager` start one (`[appium]`); for hardware-free runs use `stub=True`.

See [`examples/consumer_oracle.py`](examples/consumer_oracle.py) for a complete,
tested reference oracle.

## Public API

| Symbol | What |
|---|---|
| `Screen(screen, driver, version=…)` | the UI driver: tap/type/wait/scroll + is_present/is_enabled/get_text |
| `SessionManager`, `DeviceSpec` | session lifecycle + device descriptor |
| `load_catalog("ui.<screen>")` → `SelectorCatalog` | the selector catalog; `.locator(element, version)` → `(by, value)` |
| `Selector`, `SelectorCatalog` | the selector-catalog types |
| `register_spec_root(path)` | add/override screens for the (legacy) command-spec path |
| `CommandSpec`, `ScreenVerificationResult`, `load_command_spec[_by_name]` | legacy spec/result types |
| `catalog` | registered-command catalog: `run` / `available` / `all_specs` / `get` |
| `runtime` | env-free helpers: `device_specs_from_inventory`, `pin_specs`, `worker_index` |

Private (may change without a major bump): `registry`, `ui.base.ScreenCommand`,
`session.capabilities`, `session.stub_driver`.

> **Deprecated:** `verify_screen` / `verify_*` / `ScreenCommand` — the old *library-asserts*
> path. Still working, but the library shouldn't own expected results. Migrate to
> `Screen` + your own assertions: see
> [`docs/migration-verify-to-screen.md`](docs/migration-verify-to-screen.md). Slated for
> removal in a future major.

## Non-Python consumers — the HTTP service boundary

Non-Python clients (QWIK/TS, other apps) reach the same engine over HTTP without
reimplementing it — install `[server]`, run `atak-lib-server`, then:

```
GET    /api/selectors/<screen>[?version=]          -> selector definitions
POST   /api/session   {stub:true | device:{...}}   -> {sessionId}
DELETE /api/session/<id>                            -> {closed:true}
POST   /api/action    {sessionId, screen, element, action, args?}   # tap/type/wait_for/scroll_into_view
POST   /api/query     {sessionId, screen, element, query}           # is_present/is_enabled/get_text
```

Every response carries a versioned `schemaVersion`. The server reads no env — the
client states the target (`{"stub": true}` or a device); real-device sessions take an
injected `driver_factory`.

## Versioning across app releases

The catalog is version-aware: selectors carry per-version overrides keyed by MAJOR.MINOR
series, and `SelectorCatalog.locator(element, version)` resolves the right selector for a
build. An override of `{applies: false}` marks an element **removed** on that version —
`locator` then raises rather than returning a stale selector, and `catalog.applies(element,
version)` reports it — so older-version coverage isn't silently broken when the app
changes. Background: `docs/legacy_versioning.md`.

## The stub contract

A `StubWebDriver` (via `SessionManager([...], stub=True)`, or injected directly) runs
the whole driver with no device and no Appium — `Screen` calls resolve against an
in-memory fake. This keeps a consumer's suite green offline; on-device validation is a
separate, opt-in step (see `tests/unit/test_device_smoke.py`).

## Development

```bash
pip install -e .[dev]
pytest                                  # unit suite (stub; the library's contract)
ATAK_DEVICE_SMOKE=1 ATAK_SMOKE_UDID=<udid> pytest -m device_smoke   # opt-in, real device
```

The unit suite travels with this repo and is the library's contract.
