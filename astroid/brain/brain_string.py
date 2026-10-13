# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import importlib

from astroid.brain.helpers import register_module_extender
from astroid.const import PY314_PLUS
from astroid.manager import AstroidManager
from astroid.nodes.scoped_nodes import Module
from astroid.raw_building import InspectBuilder


def _templatelib_transform() -> Module:
    # ``string.templatelib`` defines ``Template`` and ``Interpolation`` as
    # ``type(t"...")`` / ``type(...interpolations[0])``. Those self-referential
    # assignments are not statically inferable from the source, so we rebuild
    # the real classes from the live (C) objects instead. Only those two names
    # are kept so the rest of the module is still read from its source.
    templatelib = importlib.import_module("string.templatelib")

    built = InspectBuilder(AstroidManager()).inspect_build(templatelib)
    for name in list(built.locals):
        if name not in ("Template", "Interpolation"):
            del built.locals[name]
    return built


def register(manager: AstroidManager) -> None:
    if PY314_PLUS:
        register_module_extender(manager, "string.templatelib", _templatelib_transform)
