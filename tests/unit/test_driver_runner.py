import pytest

from atak_lib.execution.driver_runner import (
    driver_runner,
    driver_runner_raise_assertion,
    driver_runner_w_exception,
    driver_runner_with_list_return,
    driver_runner_with_offset,
)


class FakeDriver:
    def __init__(self, udid):
        self.capabilities = {"udid": udid}


DRIVERS = [FakeDriver("A"), FakeDriver("B"), FakeDriver("C")]


def test_driver_runner_swallows_errors():
    hit = []

    def fn(d):
        hit.append(d.capabilities["udid"])
        raise RuntimeError("boom")
    driver_runner(fn, DRIVERS, "fn")  # must not raise
    assert sorted(hit) == ["A", "B", "C"]


def test_driver_runner_with_offset_runs_all():
    hit = []
    driver_runner_with_offset(lambda d: hit.append(d), DRIVERS, "fn", 0.0)
    assert len(hit) == 3


def test_driver_runner_with_list_return_preserves_order():
    out = driver_runner_with_list_return(
        lambda d: d.capabilities["udid"], DRIVERS, "fn")
    assert out == ["A", "B", "C"]


def test_driver_runner_w_exception_aggregates():
    def fn(d):
        if d.capabilities["udid"] == "B":
            raise ValueError("bad B")
    with pytest.raises(Exception) as exc:
        driver_runner_w_exception(fn, DRIVERS, "fn")
    assert "bad B" in str(exc.value)


def test_driver_runner_raise_assertion_propagates_first():
    def fn(d):
        raise AssertionError("assert fail")
    with pytest.raises(AssertionError):
        driver_runner_raise_assertion(fn, DRIVERS, "fn")
