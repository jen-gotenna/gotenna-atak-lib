"""Command registry -- the backbone of the modular command library.

Every command in atak_lib is a plain callable with a uniform contract:

    def command(driver, *, stub: bool = False, **params) -> Any: ...

Registering a command makes it discoverable by a dotted name (e.g.
``ui.verify_onboarding_screen``) so any runner -- a test, a Robot keyword, or the
ad-hoc CLI -- can look it up and execute it on the fly without bespoke glue. This
is what lets pieces be "dropped into runners" during manual/exploratory testing.

Pure Python: no env reads, no Appium import, no framework coupling.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List

CommandFn = Callable[..., Any]


@dataclass(frozen=True)
class CommandSpec:
    name: str            # dotted name, e.g. "ui.verify_onboarding_screen"
    fn: CommandFn
    layer: str           # ui | radio | device | session
    summary: str = ""


_REGISTRY: Dict[str, CommandSpec] = {}


def command(name: str, *, layer: str = "ui", summary: str = "") -> Callable[[CommandFn], CommandFn]:
    """Decorator: register ``fn`` under ``name``. Returns ``fn`` unchanged so it
    stays directly importable/callable."""
    def decorate(fn: CommandFn) -> CommandFn:
        resolved = summary or (fn.__doc__ or "").strip().split("\n")[0]
        register(name, fn, layer=layer, summary=resolved)
        fn.command_name = name  # type: ignore[attr-defined]
        return fn
    return decorate


def register(name: str, fn: CommandFn, *, layer: str = "ui", summary: str = "") -> None:
    if name in _REGISTRY:
        raise ValueError(f"Command already registered: {name}")
    _REGISTRY[name] = CommandSpec(name=name, fn=fn, layer=layer, summary=summary)


def get(name: str) -> CommandSpec:
    try:
        return _REGISTRY[name]
    except KeyError:
        raise KeyError(
            f"Unknown command '{name}'. Available: {', '.join(available()) or '(none loaded)'}"
        )


def available() -> List[str]:
    return sorted(_REGISTRY)


def all_specs() -> List[CommandSpec]:
    return [_REGISTRY[n] for n in available()]


def run(name: str, driver: Any, *, stub: bool = False, **params: Any) -> Any:
    """Look up and execute a registered command against ``driver``."""
    return get(name).fn(driver, stub=stub, **params)
