"""Reference: a CONSUMER's oracle built on the gotenna-atak-lib driver.

This is the pattern every consumer follows under RFC 0001's driver/oracle split, and
the replacement for the legacy in-lib ``verify_*`` path:

  * the **library** gives you selectors (the catalog) + a ``Screen`` driver that
    returns **facts** (is_present / is_enabled / get_text);
  * **your** test framework owns the **expected results** and decides pass/fail.

The library never asserts. The expectations below — which components must be present,
that Login is enabled — belong to the consumer, not the distro. A different consumer
(QWIK, another suite) brings its own expectations against the same driver.

Run the matching test: ``pytest tests/unit/test_example_oracle.py``.
"""
from __future__ import annotations

from typing import List, Optional

from atak_lib import Screen

# The CONSUMER declares its own expected component set (not the library's).
ONBOARDING_EXPECTED = [
    "logo", "logo_subtext",
    "login_button", "login_subtext",
    "deploy_qr_button", "deploy_qr_subtext",
    "manual_setup_button", "manual_setup_subtext",
    "terms_of_service_checkbox", "terms_of_service_text",
]


def check_onboarding(driver, *, version: Optional[str] = None) -> List[str]:
    """Drive + query the onboarding screen via the library, then apply the
    consumer's expectations. Returns a list of failure strings (empty == pass).

    The library only reports facts; the policy here (all expected components present,
    Login enabled) is the consumer's.
    """
    s = Screen("ui.onboarding", driver, version=version)
    failures: List[str] = []

    for element in ONBOARDING_EXPECTED:
        if not s.is_present(element):
            failures.append(f"missing component: {element}")

    # An interaction-state expectation -- also the consumer's call, not the lib's.
    if s.is_present("login_button") and not s.is_enabled("login_button"):
        failures.append("login_button is present but not enabled")

    return failures
