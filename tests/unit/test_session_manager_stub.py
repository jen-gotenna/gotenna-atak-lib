import pytest

from atak_lib.session.session_manager import DeviceSpec, SessionManager
from atak_lib.session.stub_driver import StubWebDriver


def test_stub_session_creates_stub_drivers():
    sm = SessionManager([DeviceSpec("A"), DeviceSpec("B")], stub=True)
    drivers = sm.start()
    assert len(drivers) == 2
    assert all(isinstance(d, StubWebDriver) for d in drivers)
    assert sm.driver is drivers[0]
    sm.stop()
    assert all(d.quit_called for d in drivers)


def test_stub_flag_must_be_explicit_bool():
    with pytest.raises(ValueError):
        SessionManager([DeviceSpec("A")], stub="yes")  # type: ignore


def test_context_manager():
    with SessionManager([DeviceSpec("A")], stub=True) as sm:
        assert sm.driver is not None
