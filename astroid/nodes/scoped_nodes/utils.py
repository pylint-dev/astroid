# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE

"""
This module contains utility functions for scoped nodes.
"""

import builtins
from typing import TYPE_CHECKING, List, Optional, Tuple

from astroid.manager import AstroidManager

if TYPE_CHECKING:
    from astroid import nodes


BUILTINS_AST: Optional["nodes.Module"] = None


def builtin_lookup(name: str) -> Tuple["nodes.Module", List["nodes.NodeNG"]]:
    """Lookup a name in the builtin module.

    Return the list of matching statements and the ast for the builtin module
    """
    # pylint: disable-next=global-statement
    global BUILTINS_AST
    if not BUILTINS_AST:
        BUILTINS_AST = AstroidManager().ast_from_module(builtins)
    if name == "__dict__":
        return BUILTINS_AST, ()
    try:
        stmts = BUILTINS_AST.locals[name]
    except KeyError:
        stmts = ()
    return BUILTINS_AST, stmts
