"""Multi-device parallel execution -- the driver_runner* family.

Extracted from legacy common/helpers.py. Engine-agnostic threading: each variant
runs `function(driver, *args, **kwargs)` across a list of drivers. Five variants,
matching the legacy semantics:

  driver_runner               - fire all, swallow every error
  driver_runner_with_offset   - fire all with a staggered start delay
  driver_runner_w_exception   - collect per-driver errors, raise an aggregate
  driver_runner_with_list_return - return ordered results; first error propagates
  driver_runner_raise_assertion  - run all, raise the first exception afterwards
"""
from __future__ import annotations

import concurrent.futures
import logging
import threading
from time import sleep
from typing import Any, Callable, List

log = logging.getLogger(__name__)


def _udid(driver: Any) -> str:
    try:
        return driver.capabilities.get("udid", "unknown")
    except Exception:
        return "unknown"


def driver_runner(function: Callable, drivers: List[Any], function_name: str,
                  *args: Any, **kwargs: Any) -> None:
    """Run in parallel across drivers, swallowing all exceptions."""
    log.info("Running %d drivers in parallel: %s", len(drivers), function_name)
    threads = [threading.Thread(target=function, args=(d,) + args, kwargs=kwargs)
               for d in drivers]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def driver_runner_with_offset(function: Callable, drivers: List[Any], function_name: str,
                              offset: float = 0.5, *args: Any, **kwargs: Any) -> None:
    """Like driver_runner but stagger each driver's start by `offset` seconds."""
    log.info("Running %d drivers in parallel (offset=%s): %s",
             len(drivers), offset, function_name)
    threads = [threading.Thread(target=function, args=(d,) + args, kwargs=kwargs)
               for d in drivers]
    for i, t in enumerate(threads):
        sleep(offset * i)
        t.start()
    for t in threads:
        t.join()


def driver_runner_w_exception(function: Callable, drivers: List[Any], function_name: str,
                              *args: Any, **kwargs: Any) -> None:
    """Collect per-driver errors and raise one aggregate if any occurred."""
    log.info("Running %d drivers in parallel: %s", len(drivers), function_name)
    errors = {id(d): (d, []) for d in drivers}

    def target(driver: Any, *a: Any, **kw: Any) -> None:
        try:
            function(driver, *a, **kw)
        except Exception as exc:  # noqa: BLE001 -- intentionally broad
            log.error("Error in %s on %s: %s", function_name, _udid(driver), exc)
            errors[id(driver)][1].append(str(exc))

    threads = [threading.Thread(target=target, args=(d,) + args, kwargs=kwargs)
               for d in drivers]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    failed = [(d, msgs) for d, msgs in errors.values() if msgs]
    if failed:
        detail = "\n".join(
            f"Driver {_udid(d)} encountered errors:\n" + "\n".join(msgs)
            for d, msgs in failed
        )
        raise Exception(f"One or more devices encountered errors:\n{detail}")


def driver_runner_with_list_return(function: Callable, drivers: List[Any], function_name: str,
                                   *args: Any, **kwargs: Any) -> List[Any]:
    """Return per-driver results in input order; the first error propagates."""
    log.info("Running %d drivers in parallel: %s", len(drivers), function_name)
    results: List[Any] = [None] * len(drivers)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(drivers))) as ex:
        futures = {ex.submit(function, d, *args, **kwargs): i
                   for i, d in enumerate(drivers)}
        for future in concurrent.futures.as_completed(futures):
            results[futures[future]] = future.result()
    return results


def driver_runner_raise_assertion(function: Callable, drivers: List[Any], function_name: str,
                                  *args: Any, **kwargs: Any) -> None:
    """Run all drivers, then raise the first exception encountered (if any)."""
    log.info("Running %d drivers in parallel: %s", len(drivers), function_name)
    exceptions: List[Exception] = []

    def run_and_catch(driver: Any) -> None:
        try:
            function(driver, *args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            log.error("Exception in driver %s: %s", _udid(driver), exc)
            exceptions.append(exc)

    threads = [threading.Thread(target=run_and_catch, args=(d,)) for d in drivers]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    if exceptions:
        raise exceptions[0]
