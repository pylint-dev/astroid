# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Astroid hooks for the os module."""

from astroid import nodes
from astroid.brain.helpers import register_module_extender
from astroid.builder import parse
from astroid.manager import AstroidManager


def _os_transform() -> nodes.Module:
    # The source of os.walk() takes the directory path from a stack, and differs
    # between Python versions, so the tuples it yields cannot be inferred from it.
    # The path is bytes if top is bytes, and str otherwise. The lists are left
    # empty, since they can be.
    return parse("""
    def walk(top, topdown=True, onerror=None, followlinks=False):
        yield ("" if not isinstance(top, bytes) else b""), [], []
    """)


def register(manager: AstroidManager) -> None:
    register_module_extender(manager, "os", _os_transform)
