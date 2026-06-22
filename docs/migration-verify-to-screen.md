# Migration: in-lib `verify_*` → `Screen` + consumer-owned assertions

**Why:** under RFC 0001 the library is a **driver** (selectors + manipulation + state,
returns facts); the **consumer** owns expected results. The old in-lib `verify_*` /
`ScreenCommand` path fused both — the library decided pass/fail. That's being retired
so every consumer (this team's pytest suite, QWIK, future apps) brings its own
expectations against one shared driver.

## Before — the library asserts

```python
from atak_lib import verify_screen   # legacy: library owns the expectations

result = verify_screen("ui.verify_onboarding_screen", driver)
assert result.passed, result.failures
```

## After — the library reports facts; you assert

```python
from atak_lib import Screen

s = Screen("ui.onboarding", driver, version="3.0")
# YOUR expectations live here, in YOUR repo:
assert s.is_present("login_button")
assert s.is_enabled("login_button")
assert s.get_text("terms_of_service_text") == "I agree to the Terms of Service"
```

See [`examples/consumer_oracle.py`](../examples/consumer_oracle.py) for a complete,
tested reference (a `check_onboarding(driver)` oracle that returns a failure list).

## What moves where

| Concern | Before (lib) | After |
|---|---|---|
| Selector `by`/`value`, version resolution | lib YAML | **lib** — `atak_lib.selectors` catalog |
| Find / tap / type / wait / state | lib (engine) | **lib** — `atak_lib.Screen` |
| "component must be present / enabled" | lib YAML (`this_build_present`, `expect_enabled`) | **consumer** — your assertions |
| Expected text | lib YAML | **consumer** |
| Lenient-vs-strict pass/fail policy | lib (`lenient_if_unconfirmed`) | **consumer** |
| TestRail case mapping, reporting (Allure) | lib spec / adapter | **consumer** |

## Status of the legacy path

`verify_screen`, the `verify_*` functions, and `ScreenCommand` still work today and
are unchanged — they remain available during migration. They are **legacy** under the
driver/oracle split and are slated for **removal in a future major** once consumers
have migrated to `Screen`. New code should use `Screen` + its own assertions.

## For this team's pytest framework (`atak-plugin-v3-qa-automation`)

The framework rewiring (replace its `verify_*` calls with `Screen` + an oracle like
the example) lands **after** a library release that includes the catalog + `Screen`
(i.e. once the RFC 0001 PRs merge and `v0.2.0` is cut). Until then the framework keeps
consuming `v0.1.0` and its current verify path.
