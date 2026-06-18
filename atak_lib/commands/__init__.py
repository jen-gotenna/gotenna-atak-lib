"""Packaged command specs (YAML, the single source of truth).

These YAML files ship *inside* the wheel so a pip-installed ``atak_lib`` can find
its specs via :mod:`importlib.resources` (see :mod:`atak_lib.spec`). They are data,
not code -- this package exists only to make ``atak_lib.commands`` importable and
its ``*.yaml`` resources discoverable from a source tree, an installed wheel, or a
zipapp.
"""
