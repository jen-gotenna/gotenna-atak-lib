# Changelog

All notable changes to `gotenna-atak-lib` are documented here. This project adheres
to [Semantic Versioning](https://semver.org/). The **YAML spec schema** and the
**locator-status contract** (`CONFIRMED` / `CROSS_CONFIRMED` / `UNCONFIRMED`,
`legacy_confirmed`, per-version overrides) are part of the public, versioned surface
— breaking changes to them require a major bump.

## [Unreleased]

### Added (RFC 0001 — shared UI driver, in progress toward v0.2.0)
- **Selector catalog** (`atak_lib.selectors`) — an addressable element inventory
  holding **definitions only** (`by`/`value` + resolvability: `status`,
  `legacy_confirmed`, per-version overrides). No assertions/expected results — those
  belong to the consuming test framework. Version-aware via the same MAJOR.MINOR
  series matching as the locator model; ships as packaged YAML
  (`atak_lib/selectors/<layer>/<screen>.yaml`). API: `load_catalog("ui.<screen>")`,
  `catalog.locator(element, version)`, `selectors.locator(screen, element, version)`.
- First catalog: `ui/onboarding.yaml` (10 selectors, migrated from the verify spec).
- A per-target override axis is **reserved** (not yet resolved) so non-Android
  targets (e.g. a Flutter app addressed by semantic label) are additive later.
- **`Screen` manipulation + state facade** (`atak_lib.Screen`) — drives an injected
  Appium WebDriver via catalog-resolved selectors: `tap`, `type`, `wait_for`,
  `scroll_into_view`, and the fact-returning `is_present` / `is_enabled` / `get_text`.
  Returns facts, never pass/fail (assertions belong to consumers). Accepts a dotted
  catalog name or a consumer-supplied `SelectorCatalog`; version-aware. Public API now
  exports `Screen`, `Selector`, `SelectorCatalog`. `StubWebDriver` gained
  `click`/`send_keys`/`clear`/`is_enabled` (+ interaction logs) so the facade is
  fully exercisable offline.

> The existing `verify_*` / `assertions` path is unchanged and still works; the
> catalog is added alongside. Moving assertions out to consumers + the manipulation
> API land in subsequent steps. This is a breaking-direction effort tracked for v0.2.0.

## [0.1.0] — extracted from the v3 QA automation suite

First standalone release. Extracted from `atak-plugin-v3-qa-automation` (QA-3920),
where the driver was built env-agnostic from the start.

### Added
- **Packaged command specs.** YAML specs ship inside the wheel under
  `atak_lib/commands/` and load via `importlib.resources`, so an installed wheel
  finds its specs from any working directory.
- **`register_spec_root(path)`** — consumers add or override screens without forking
  the library; registered roots are searched before packaged specs.
- **`verify_screen(command_name, driver, ...)`** — generic, declarative runner that
  resolves a spec by dotted name (honoring `register_spec_root`) and runs the
  soft-assert engine. The no-Python-authoring extension path.
- **`atak_lib.runtime`** — env-free runtime helpers: `device_specs_from_inventory`
  (DeviceSpec construction from parsed data + injected stub/udid resolver) and the
  parallel pinning helpers (`pin_specs`, `worker_index`, `BASE_SYSTEM_PORT`).
- **Public API + `py.typed`.** `atak_lib/__init__.py` defines the stable surface and
  ships type hints (PEP 561). Importing `atak_lib` reads no env and does not import
  Appium.
- **Version-aware specs.** `supported_versions`, per-locator `versions` overrides, and
  `CommandSpec.for_version()` resolve locators per app version so legacy coverage is
  preserved across releases. See `docs/legacy_versioning.md` (in the framework repo).

### Notes
- Appium is a lazy/optional dependency (`pip install gotenna-atak-lib[appium]`); the
  only hard runtime dependency is PyYAML.
- `atak_lib` stays env-agnostic: it never reads environment variables. The env/stub
  read lives in the consuming framework's adapter layer.
