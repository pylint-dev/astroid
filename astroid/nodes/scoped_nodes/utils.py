# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

"""
This module contains utility functions for scoped nodes.
"""

from __future__ import annotations

import builtins
from collections.abc import Sequence
from typing import TYPE_CHECKING

from astroid.manager import AstroidManager

if TYPE_CHECKING:
    from astroid import nodes


def builtin_lookup(name: str) -> tuple[nodes.Module, Sequence[nodes.NodeNG]]:
    """Lookup a name in the builtin module.

    Return the list of matching statements and the ast for the builtin module
    """
    try:
        _builtin_astroid = AstroidManager().builtins_module
    except KeyError:
        _builtin_astroid = AstroidManager().ast_from_module(builtins)
    if name == "__dict__":
        return _builtin_astroid, ()
    try:
        stmts: Sequence[nodes.NodeNG] = _builtin_astroid.locals[name]
    except KeyError:
        stmts = ()
    return _builtin_astroid, stmts
