# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Astroid hooks for orjson's serialization functions."""

from astroid import nodes
from astroid.brain.helpers import register_module_extender
from astroid.builder import parse
from astroid.manager import AstroidManager


def _orjson_transform() -> nodes.Module:
    return parse("""
    def dumps(obj, /, default=None, option=None):
        return b''

    def loads(obj, /):
        return uninferable
    """)


def register(manager: AstroidManager) -> None:
    register_module_extender(manager, "orjson", _orjson_transform)
