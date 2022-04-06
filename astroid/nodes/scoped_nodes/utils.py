# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

"""
This module contains utility functions for scoped nodes.
"""

import builtins
from typing import TYPE_CHECKING, Sequence, Tuple

from astroid.manager import AstroidManager

if TYPE_CHECKING:
    from astroid import nodes


_builtin_astroid: "nodes.Module | None" = None


def builtin_lookup(name: str) -> Tuple["nodes.Module", Sequence["nodes.NodeNG"]]:
    """Lookup a name in the builtin module.

    Return the list of matching statements and the ast for the builtin module
    """
    # pylint: disable-next=global-statement
    global _builtin_astroid
    if _builtin_astroid is None:
        _builtin_astroid = AstroidManager().ast_from_module(builtins)
    if name == "__dict__":
        return _builtin_astroid, ()
    try:
        stmts: Sequence["nodes.NodeNG"] = _builtin_astroid.locals[name]
    except KeyError:
        stmts = ()
    return _builtin_astroid, stmts
