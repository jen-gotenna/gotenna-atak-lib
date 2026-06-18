"""Screen-navigation preconditions for on-device UI checks.

The verify_* commands soft-assert against whatever screen is currently active;
they do NOT navigate. These helpers put the goTenna plugin on the right screen
first, so a real-device run is deterministic instead of depending on whatever the
app was last left on (the wrong-screen flake).

Pure driver logic: takes an injected WebDriver, reads no env, imports no Appium
(uses Appium's string locator strategies directly). Every UI call is guarded so a
non-driving driver (e.g. StubWebDriver) is a safe no-op -- callers skip these in
stub mode anyway.

Locators are intentionally inline here (navigation glue, not a screen spec); the
asserted screen contracts live in the YAML specs.
"""
from __future__ import annotations

import logging
import time
from typing import Any

log = logging.getLogger(__name__)

# Appium string strategies (no appium import needed to keep atak_lib import-light).
_ID = "id"
_UIA = "-android uiautomator"

# Core + plugin nav locators (confirmed on ATAK-CIV 5.7.0.3 / plugin 3.0.0).
_ATAK_PKG = "com.atakmap.app.civ"
_NAV_MENU_BUTTON = "com.atakmap.app.civ:id/tak_nav_menu_button"
_GOTENNA_MENU_ITEM = 'new UiSelector().text("goTenna")'
_PLUGIN_MAIN = "com.gotenna.atak:id/mainContainer"
_LOGIN_BUTTON = "com.gotenna.atak:id/loginButton"
_DEVICE_CARD = "com.gotenna.atak:id/deviceCard"
# Device Details spans more than one viewport: a top anchor and a bottom anchor, so
# "are we on Device Details?" can be answered without scrolling (present-check either).
_DEVICE_DETAILS_ANCHOR = "com.gotenna.atak:id/deviceDetailsStatusTextView"
_DEVICE_DETAILS_BOTTOM = "com.gotenna.atak:id/deviceDetailsListenOnlyModeContainer"
_ANTENNA_IGNORE_BTN = "android:id/button3"   # "Ignore" on the bad-antenna warning
# "Set as Relay" flow (C149725): the Device Details page button that OPENS the
# confirm dialog, and the dialog's own anchors. The dialog is a standard Android
# AlertDialog (android:id/*). We only ever tap CANCEL (button2) -- confirming
# (button1) sets relay mode and disconnects the radio.
_RELAY_MODE_BUTTON = "com.gotenna.atak:id/deviceDetailsRelayModeButton"
_DIALOG_TITLE = "android:id/alertTitle"
_DIALOG_CANCEL = 'new UiSelector().resourceId("android:id/button2").text("Cancel")'


def _present(driver: Any, by: str, value: str) -> bool:
    try:
        return len(driver.find_elements(by, value)) > 0
    except Exception:
        return False


def _tap(driver: Any, by: str, value: str) -> bool:
    try:
        els = driver.find_elements(by, value)
        if els:
            els[0].click()
            return True
    except Exception as exc:
        log.debug("tap %s=%s failed: %s", by, value, exc)
    return False


def _wait_any(driver: Any, locators, timeout: float = 4.0,
              interval: float = 0.2) -> bool:
    """Poll until any of ``locators`` (``(by, value)`` tuples) is present.

    Condition-based wait instead of a fixed sleep: returns as soon as the screen
    is ready (so navigation is no slower than the device), or False on timeout.
    The interval sleep is poll cadence, not a readiness guess.
    """
    deadline = time.time() + timeout
    while True:
        if any(_present(driver, by, val) for by, val in locators):
            return True
        if time.time() >= deadline:
            return False
        time.sleep(interval)


def _wait_gone(driver: Any, by: str, value: str, timeout: float = 2.0,
               interval: float = 0.2) -> bool:
    """Poll until ``value`` is no longer present (e.g. a dialog has dismissed)."""
    deadline = time.time() + timeout
    while True:
        if not _present(driver, by, value):
            return True
        if time.time() >= deadline:
            return False
        time.sleep(interval)


def _on_device_details(driver: Any) -> bool:
    """True if the Device Details page is showing, at ANY scroll position.

    Cheap present-check (no scroll): the page has a top anchor and a bottom anchor,
    so whichever end is in view, one of them resolves. This deliberately avoids
    UiAutomator ``scrollIntoView`` here -- on the radio-status card (where the
    anchor isn't present yet) scrollIntoView would burn ~3s fruitlessly searching
    the pane before we tap the device card. The verifier handles the actual
    scrolling once we're on the page.
    """
    return (_present(driver, _ID, _DEVICE_DETAILS_ANCHOR) or
            _present(driver, _ID, _DEVICE_DETAILS_BOTTOM))


def dismiss_antenna_warning(driver: Any) -> bool:
    """Dismiss the goTenna "Antenna is bad!" warning (session-scoped Ignore) if up.

    Returns True if a warning was dismissed. The dialog can overlay the radio
    screens and block navigation/assertions.
    """
    try:
        els = driver.find_elements(_ID, _ANTENNA_IGNORE_BTN)
        if els and str(els[0].text).strip().lower() == "ignore":
            els[0].click()
            _wait_gone(driver, _ID, _ANTENNA_IGNORE_BTN, timeout=2.0)
            return True
    except Exception as exc:
        log.debug("antenna warning dismiss failed: %s", exc)
    return False


def _foreground_atak(driver: Any) -> None:
    try:
        driver.activate_app(_ATAK_PKG)
        # Wait for ATAK to be interactable (any of these means it's up).
        _wait_any(driver, [(_ID, _PLUGIN_MAIN), (_ID, _DEVICE_CARD),
                           (_ID, _NAV_MENU_BUTTON)], timeout=3.0)
    except Exception as exc:
        log.debug("activate_app failed: %s", exc)


def open_gotenna_plugin(driver: Any) -> None:
    """Bring ATAK forward and select the goTenna plugin tool (nav menu -> goTenna).

    No-op if the plugin pane (or device card) is already showing.
    """
    _foreground_atak(driver)
    dismiss_antenna_warning(driver)
    if _present(driver, _ID, _PLUGIN_MAIN) or _present(driver, _ID, _DEVICE_CARD):
        return
    if _tap(driver, _ID, _NAV_MENU_BUTTON):
        # Wait for the goTenna menu item to render, tap it, wait for the pane.
        if _wait_any(driver, [(_UIA, _GOTENNA_MENU_ITEM)], timeout=3.0):
            _tap(driver, _UIA, _GOTENNA_MENU_ITEM)
            _wait_any(driver, [(_ID, _PLUGIN_MAIN), (_ID, _DEVICE_CARD)], timeout=4.0)


def open_onboarding(driver: Any) -> bool:
    """Put the plugin on the onboarding home screen (logged out, no radio).

    Returns True if the onboarding home anchor is present afterward.
    """
    open_gotenna_plugin(driver)
    return _present(driver, _ID, _PLUGIN_MAIN) and _present(driver, _ID, _LOGIN_BUTTON)


def open_device_details(driver: Any) -> bool:
    """Put the plugin on the Device Details page (requires a connected radio).

    Opens the plugin, taps the device card to drill into details, and dismisses the
    bad-antenna warning if it appears. Returns True if the Device Details anchor is
    present afterward.
    """
    open_gotenna_plugin(driver)
    dismiss_antenna_warning(driver)
    # Already on Device Details (any scroll position)? Cheap check, no scroll.
    if _on_device_details(driver):
        return True
    # On the radio status card (not yet drilled in): tap the card to open details,
    # then wait for either Device Details anchor to render (condition, not a sleep).
    if _tap(driver, _ID, _DEVICE_CARD):
        _wait_any(driver, [(_ID, _DEVICE_DETAILS_ANCHOR),
                           (_ID, _DEVICE_DETAILS_BOTTOM)], timeout=4.0)
    dismiss_antenna_warning(driver)
    return _on_device_details(driver)


def open_set_as_relay_dialog(driver: Any) -> bool:
    """Open the "Set as Relay" confirm dialog from Device Details (C149725).

    Brings up the plugin, makes sure the Device Details "Set as Relay" button is on
    screen (scrolls to it if needed -- some builds show a combined card/tabs layout
    where the page anchors aren't where ``_on_device_details`` expects), taps it to
    OPEN the dialog, and waits for the dialog. Returns True if the dialog is up.

    Tapping the page button only OPENS the confirm dialog; it does NOT set relay
    mode. Dismiss with :func:`cancel_set_as_relay_dialog` -- never tap the dialog's
    confirm button (that sets relay mode and disconnects the radio).
    """
    open_gotenna_plugin(driver)
    dismiss_antenna_warning(driver)
    # Make sure the relay button is rendered; scroll it into view if it isn't.
    if not _present(driver, _ID, _RELAY_MODE_BUTTON):
        try:
            driver.find_element(
                _UIA,
                "new UiScrollable(new UiSelector().scrollable(true))"
                '.scrollIntoView(new UiSelector().resourceId("%s"))'
                % _RELAY_MODE_BUTTON)
        except Exception as exc:
            log.debug("scroll to relay button failed: %s", exc)
    if not _tap(driver, _ID, _RELAY_MODE_BUTTON):
        return False
    return _wait_any(driver, [(_ID, _DIALOG_TITLE), (_UIA, _DIALOG_CANCEL)],
                     timeout=4.0)


def cancel_set_as_relay_dialog(driver: Any) -> bool:
    """Dismiss the "Set as Relay" confirm dialog via Cancel (button2) ONLY.

    Safety helper: tests must call this to back out without ever tapping the
    confirm button (button1), which would set relay mode and disconnect the radio.
    Returns True if the dialog was dismissed (or was already gone).
    """
    if not _present(driver, _ID, _DIALOG_TITLE):
        return True
    if _tap(driver, _UIA, _DIALOG_CANCEL):
        return _wait_gone(driver, _ID, _DIALOG_TITLE, timeout=2.0)
    return False
