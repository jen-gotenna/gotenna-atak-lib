"""Screen facade: manipulation + state over an injected driver, against the stub.

State queries return facts; manipulation drives the driver. No assertions live here
(that's the consumer's job) -- these tests verify the *mechanism*: catalog-resolved
selectors turned into find_element / click / send_keys / is_enabled calls.
"""
from atak_lib import Screen
from atak_lib.selectors import load_catalog_file
from atak_lib.session.stub_driver import StubWebDriver

LOGIN = ("id", "com.gotenna.atak:id/loginButton")
TERMS_TEXT = ("id", "com.gotenna.atak:id/termsCheckboxText")


# ---- state queries (facts) --------------------------------------------------

def test_is_present_true_when_driver_has_it():
    s = Screen("ui.onboarding", StubWebDriver(present_all=True))
    assert s.is_present("login_button") is True


def test_is_present_false_when_absent():
    s = Screen("ui.onboarding", StubWebDriver(present_all=False, present=set()))
    assert s.is_present("login_button") is False


def test_get_text_returns_driver_text():
    drv = StubWebDriver(present_all=True, texts={TERMS_TEXT: "I agree to the Terms"})
    s = Screen("ui.onboarding", drv)
    assert s.get_text("terms_of_service_text") == "I agree to the Terms"


def test_is_enabled_reads_element_state():
    enabled = Screen("ui.onboarding", StubWebDriver(present_all=True))
    assert enabled.is_enabled("login_button") is True
    disabled = Screen("ui.onboarding", StubWebDriver(
        present_all=True, attributes={LOGIN: {"enabled": "false"}}))
    assert disabled.is_enabled("login_button") is False


# ---- manipulation -----------------------------------------------------------

def test_tap_resolves_selector_and_clicks():
    drv = StubWebDriver(present_all=True)
    Screen("ui.onboarding", drv).tap("login_button")
    assert drv.taps == [LOGIN]


def test_type_clears_then_sends_keys():
    # A consumer-owned catalog with an input field (Screen accepts a catalog object).
    import textwrap
    import tempfile
    import os
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "ui"))
    path = os.path.join(d, "ui", "form.yaml")
    with open(path, "w") as f:
        f.write(textwrap.dedent("""
            screen: form
            selectors:
              name_field: { by: id, value: com.x:id/name, status: CONFIRMED }
        """))
    drv = StubWebDriver(present_all=True)
    Screen(load_catalog_file(path), drv).type("name_field", "alice")
    assert drv.cleared == [("id", "com.x:id/name")]
    assert drv.typed == [("id", "com.x:id/name", "alice")]


def test_type_without_clear():
    drv = StubWebDriver(present_all=True)
    Screen("ui.onboarding", drv).type("login_button", "x", clear=False)
    assert drv.cleared == []
    assert drv.typed == [(*LOGIN, "x")]


# ---- waits & scroll ---------------------------------------------------------

def test_wait_for_present_returns_true_immediately():
    s = Screen("ui.onboarding", StubWebDriver(present_all=True))
    assert s.wait_for("login_button", timeout=0) is True


def test_wait_for_absent_times_out_without_hanging():
    s = Screen("ui.onboarding", StubWebDriver(present_all=False, present=set()))
    assert s.wait_for("login_button", timeout=0) is False


def test_scroll_into_view_is_guarded_and_returns_presence():
    # Stub can't really scroll; the call is swallowed and we get a presence check.
    s = Screen("ui.onboarding", StubWebDriver(present_all=True))
    assert s.scroll_into_view("login_button") is True


def test_version_is_threaded_into_resolution():
    import textwrap
    import tempfile
    import os
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "ui"))
    path = os.path.join(d, "ui", "v.yaml")
    with open(path, "w") as f:
        f.write(textwrap.dedent("""
            screen: v
            supported_versions: ["3.0", "3.2"]
            selectors:
              btn:
                by: id
                value: base.id
                status: CONFIRMED
                versions:
                  "3.2": { value: new.id }
        """))
    cat = load_catalog_file(path)
    Screen(cat, StubWebDriver(present_all=True), version="3.2").tap("btn")
    drv = StubWebDriver(present_all=True)
    Screen(cat, drv, version="3.2").tap("btn")
    assert drv.taps == [("id", "new.id")]


def test_is_present_false_for_element_removed_on_version():
    # An element removed on a version (applies: false) is absent -> is_present False,
    # NOT a raise -- even when the driver would report everything present.
    import os
    import tempfile
    import textwrap
    from atak_lib.selectors import load_catalog_file
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "ui"))
    path = os.path.join(d, "ui", "rm.yaml")
    with open(path, "w") as f:
        f.write(textwrap.dedent("""
            screen: rm
            supported_versions: ["3.0", "3.2"]
            selectors:
              gone:
                by: id
                value: a
                status: CONFIRMED
                versions:
                  "3.2": { applies: false }
        """))
    cat = load_catalog_file(path)
    drv = StubWebDriver(present_all=True)          # driver says everything present...
    assert Screen(cat, drv, version="3.2").is_present("gone") is False   # ...catalog wins
    assert Screen(cat, drv, version="3.0").is_present("gone") is True
