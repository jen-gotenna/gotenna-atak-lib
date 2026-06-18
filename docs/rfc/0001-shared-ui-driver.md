# RFC 0001 — `gotenna-atak-lib` as a shared UI driver

**Status:** proposal (for review) · **Target release:** `gotenna-atak-lib` v0.2.0
(semver-breaking) · **Tracking:** sub-task under epic QA-3916 · **Supersedes parts
of:** the v3 verification-suite data model.

> Decision needed before any code: the boundaries in §5 and §7, and the open
> questions in §10. No schema changes land until this RFC is accepted.

## 1. Problem

Today `gotenna-atak-lib` is a **verification suite**: each YAML spec fuses a
*selector* (`by`/`value`) with an *assertion* (`expect_present`, `expect_enabled`,
expected text, `status`, TestRail mapping, stub expectations), and the soft-assert
engine lives in the library. That shape was right for the v3 POC, but it does not
serve the actual goal:

- **A general-purpose driver for an open-ended consumer set** — this team's pytest
  framework, QWIK (TS), and likely other apps/tooling. Not a one-consumer
  integration.
- **Consumers must not redefine selectors inline in their own repos.** The library
  is the single home for *every* selector and the UI manipulation to act on it.
- **Expected results belong to each consumer**, not the library. Observation and
  judgement are different jobs.

## 2. Goal

Make the distro hold **all selector definitions + all UI manipulation/state**, so any
consumer can find, drive, and read the ATAK UI without re-declaring a locator —
while each consumer keeps its **own** assertions. One selector source of truth; one
manipulation engine; many oracles.

## 3. Separation of concerns (the core principle)

| | Lives in | Responsibility |
|---|---|---|
| **Selector catalog** | **lib** | how to address each element, version-aware |
| **UI manipulation + state** | **lib** | drive (tap/type/swipe/wait) and observe (is_present/is_enabled/get_text) — returns **facts** |
| **Expected results / assertions** | **consumer** | what *should* be true on a build; pass/fail; leniency policy |
| **Reporting / case mapping** (Allure, TestRail) | **consumer** | how results are recorded |

The library **observes**; the consumer **judges**. The library never returns
pass/fail — only state.

## 4. Architecture — one engine, two front doors

```
                    ┌─────────────────────────── gotenna-atak-lib ───────────────────────────┐
                    │  Selector catalog (YAML, version-aware)  ──►  resolve(screen, element)  │
                    │  Manipulation + state API  ──►  injected Appium WebDriver               │
                    └─────────────▲───────────────────────────────────────▲───────────────────┘
                                  │ import (in-process)                    │ HTTP (process boundary)
                    ┌─────────────┴─────────────┐            ┌─────────────┴──────────────────┐
                    │ Python consumers           │            │ Non-Python consumers           │
                    │ (this pytest framework,     │            │ (QWIK/TS, other apps/langs)    │
                    │  other suites, tooling)     │            │  via the service boundary      │
                    │  + their OWN assertions     │            │  + their OWN assertions        │
                    └────────────────────────────┘            └────────────────────────────────┘
```

- **Native Python API (first-class).** Python consumers `import atak_lib` and drive
  in-process. Serves this framework and any Python suite/tooling with no indirection.
- **Service boundary (the language bridge).** The *same* engine over HTTP for
  non-Python consumers; manipulation runs **server-side in the lib**, so they never
  reimplement the driver or hold selectors. (This is Path B from the extraction plan.)
- **Optional read-only catalog export** — selectors as generated JSON (from the YAML)
  for any consumer that only wants to *introspect*. Still single-source; no engine
  duplication. (Explicit non-goal: do **not** port the manipulation/locator engine to
  a second language.)

## 5. Data model

Split each screen's YAML into a **selector catalog** with no assertion fields.
Version-awareness (the existing `supported_versions` + per-locator `versions`
override machinery) is preserved — it's how the catalog serves the right selector per
app version, which is the backward-compatibility requirement.

```yaml
screen: onboarding
layer: ui
supported_versions: ["3.0"]            # series this catalog is maintained for
selectors:
  login_button:
    by: id                              # Appium locator strategy (passes straight to find_element)
    value: com.gotenna.atak:id/login_button
    status: CONFIRMED                   # selector RESOLVABILITY on the baseline (see §5.2)
    legacy_confirmed: false
    versions:                           # per-version overrides (rename/move/removed)
      "3.2": { value: com.gotenna.atak:id/login_v2, status: UNCONFIRMED }
  username_field:
    by: id
    value: com.gotenna.atak:id/username
    status: CONFIRMED
```

### 5.1 Field migration (from today's fused spec)

| Field (today) | Destination |
|---|---|
| `by`, `value` | **lib catalog** (selector) |
| `status`, `legacy_confirmed`, `versions` | **lib catalog** (selector resolvability, §5.3) |
| `expect_present` / `this_build_present` | **consumer** (expected result) |
| `expect_enabled` | **consumer** |
| expected text / required strings | **consumer** |
| `stub_returns` | **consumer** (its stub oracle) |
| `testrail.case_id`, `applies_to` | **consumer** (case mapping) |
| soft-assert engine (`ScreenCommand`, `ScreenVerificationResult`) | **consumer** |

### 5.2 Target/platform dimension — forward-compat (e.g. Flutter)

The catalog may eventually need to address **non-Android-native targets** — notably a
**Flutter app, located by semantic labels** rather than Android resource-ids. The
model is already positioned for this:

- `by` is an opaque Appium **strategy string**, not Android-specific. Flutter
  `Semantics(label:)` nodes surface to the Android a11y tree as `content-desc`, so they
  resolve via `by: accessibility id` with the **standard UiAutomator2 driver** — no new
  locator type needed. (Richer control via the Appium Flutter Driver's
  `byValueKey` / `bySemanticsLabel` finders is also expressible as strategy strings.)
- The **injected-driver** contract (§7) lets a Flutter-capable Appium driver swap in
  **without touching the catalog or the manipulation API** — the command path
  (`find_element` + actions) is identical.
- The genuinely new axis is **which target** a logical element belongs to. The same
  per-version override mechanism **generalizes to a target/platform axis**, so one
  stable element name resolves to the right locator per app (native ATAK vs a Flutter
  app) and platform.

Recommendation: keep `by` strategy-agnostic (already true) and **reserve** a
target/platform dimension in the v0.2.0 schema design — even if only Android-native is
implemented now — so adding Flutter (or iOS, or a web target) later is *additive*, not
a breaking reshuffle. See §10.

### 5.3 Boundary decision — locator `status` / version-gating

Recommendation: **selector resolvability stays in the catalog.** `status`
(CONFIRMED / CROSS_CONFIRMED / UNCONFIRMED), `legacy_confirmed`, and the per-version
overrides describe *whether/how a locator resolves on a build* — a property of the
selector, and the mechanism that serves backward-compat per app version. What moves
to consumers is the *expectation* (must be present/enabled/have text) and the
**lenient-vs-strict pass/fail policy**. (Open for debate — see §10.)

## 6. API sketch

### 6.1 Python (native, first-class)

```python
from atak_lib import Screen, catalog

# raw catalog (definitions only)
by, value = catalog.locator("ui.onboarding", "login_button", version="3.2")

# manipulation + state against an INJECTED driver (real, or SessionManager-created, or stub)
s = Screen("ui.onboarding", driver, version="3.2")
s.tap("login_button")
s.type("username_field", "alice")
present  = s.is_present("deploy_qr_button")   # fact
enabled  = s.is_enabled("login_button")       # fact
label    = s.get_text("logo_subtext")         # fact
s.wait_for("device_details_title", timeout=10)
s.scroll_into_view("manual_setup_button")
```
The consumer then asserts: `assert present`, `assert label == "Terms of Use"`, etc.
— in *its* repo, with *its* expectations.

### 6.2 Service (non-Python consumers)

```
GET  /selectors/{screen}?version=3.2     -> {element: {by, value, status}, ...}   (introspection)
POST /action  {device, screen, element, action, args, version}  -> {ok, state}
POST /query   {device, screen, element, query, version}         -> {value}        (fact)
```
The server holds the `SessionManager`/driver and turns each request into the same
`find_element` + WebElement calls described in §7.

## 7. How the lib drives — the mechanism

Manipulation resolves a *named* selector from the catalog to `(by, value)` and issues
standard WebDriver calls against an **injected** Appium driver:

```python
by, value = catalog.locator(screen, element, version)   # ("id", "com.gotenna.atak:id/login_button")
el = driver.find_element(by, value)                      # driver injected by the consumer/SessionManager
el.click()                                               # or send_keys / .text / .is_enabled / .is_displayed
# gestures: driver.execute_script("mobile: scrollGesture", {...})   # UiAutomator2
```

- The catalog's `by` values **are** Appium strategy strings (`id`, `accessibility
  id`, `-android uiautomator`), so they pass straight to `find_element` (the lib needs
  no Selenium import; `Locator.as_tuple()` already returns this form).
- The driver is **injected** — the lib depends only on the WebDriver interface, so it
  works with a consumer-supplied driver, a `SessionManager`-created one (lazy Appium),
  or `StubWebDriver` in stub/CI. The command path is identical in all three.
- For non-Python consumers, the driver object lives **server-side**; the command path
  is unchanged.
- The injected-driver contract is also what lets the *same* catalog + manipulation API
  drive **other UI stacks later** — e.g. a Flutter app via a Flutter-capable Appium
  driver, with semantic labels as `accessibility id` values (§5.2). Unchanged command
  path; only the injected driver and the catalog's `by`/`value` differ.

## 8. Backward compatibility

- **Plugin-version compat (hard requirement):** preserved and central — the catalog
  keeps `supported_versions` + per-version overrides + `for_version()` resolution, so
  a selector that moves/is removed in a later build doesn't break older-version
  coverage. See `docs/legacy_versioning.md`.
- **The v3 verification suite:** its *selectors* move into the catalog unchanged; its
  *expectations* move into this team's pytest framework (a thin `ScreenCommand`-style
  helper there, consuming the lib's state queries). Net behavior preserved; the
  onboarding 10/10-CONFIRMED result still holds, now expressed as framework assertions
  over lib-provided state.
- **Semver:** this is a breaking schema + API change → **v0.2.0**, with a `CHANGELOG`
  entry, a migration note, and contract tests pinning the new catalog schema + service
  wire format.

## 9. Phasing (proposed, after acceptance)

1. **Catalog layer** — new YAML schema + loader + `catalog.locator()`; migrate the
   existing specs (selectors only); contract test. Keep the old verify path working in
   parallel (deprecated) so nothing breaks mid-migration.
2. **Manipulation/state API** — `Screen` facade (tap/type/wait/scroll + is_present/
   is_enabled/get_text) over the injected driver; stub-mode parity.
3. **Move assertions out** — port the expectation half of the v3 specs into the pytest
   framework as its oracle; retire the in-lib soft-assert path.
4. **Service boundary (Path B)** — `/selectors`, `/action`, `/query` + schema contract
   test + a thin client; optional JSON catalog export.

## 10. Open questions

1. **Status/version-gating boundary (§5.3)** — confirm selector resolvability stays in
   the catalog while pass/fail leniency moves to consumers.
2. **Manipulation scope** — start minimal (tap/type/wait/get_text/is_present/
   is_enabled/scroll) or include more gestures (long-press, drag, multi-touch) now?
3. **Service session lifecycle** — per-request session vs. an open/close
   `/session` returning a reusable id (the extraction plan leaned to the latter for the
   provision-then-verify sequence).
4. **Catalog export** — ship the read-only JSON export in v0.2.0, or defer until a
   consumer asks?
5. **Target/platform dimension (§5.2)** — reserve a target/platform axis in the v0.2.0
   schema now (Android-native implemented; Flutter/iOS/web additive later), or defer?
   Recommendation: reserve it now so future targets stay additive, not breaking.

## 11. Non-goals

- Porting the manipulation/locator engine to TS or any second language (one engine;
  non-Python consumers use the service).
- The library asserting expected results, mapping TestRail cases, or owning reporting —
  those are consumer concerns.
- Auto-generating consumer screens — consumers register their own spec dirs
  (`register_spec_root`) if they need screens beyond the shared catalog.
