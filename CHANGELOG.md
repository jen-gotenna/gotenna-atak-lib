# Changelog

All notable changes to `gotenna-atak-lib` are documented here. This project adheres
to [Semantic Versioning](https://semver.org/). The **YAML spec schema** and the
**locator-status contract** (`CONFIRMED` / `CROSS_CONFIRMED` / `UNCONFIRMED`,
`legacy_confirmed`, per-version overrides) are part of the public, versioned surface
— breaking changes to them require a major bump.

## [Unreleased]

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
