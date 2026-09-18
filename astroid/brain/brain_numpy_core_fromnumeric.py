# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Astroid hooks for numpy.core.fromnumeric and numpy._core.fromnumeric modules."""

from astroid import nodes
from astroid.brain.helpers import register_module_extender
from astroid.builder import parse
from astroid.manager import AstroidManager


def numpy_core_fromnumeric_transform() -> nodes.Module:
    return parse("""
    def sum(a, axis=None, dtype=None, out=None, keepdims=None, initial=None):
        return numpy.ndarray([0, 0])
    """)


def register(manager: AstroidManager) -> None:
    register_module_extender(
        manager, "numpy.core.fromnumeric", numpy_core_fromnumeric_transform
    )
    # NumPy 2.0 renamed numpy.core to numpy._core; keep both hooks.
    register_module_extender(
        manager, "numpy._core.fromnumeric", numpy_core_fromnumeric_transform
    )
