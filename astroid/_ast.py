# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import ast
from typing import Final, NamedTuple

from astroid.const import Context


class FunctionType(NamedTuple):
    argtypes: list[ast.expr]
    returns: ast.expr


def parse_function_type_comment(type_comment: str) -> FunctionType | None:
    """Given a correct type comment, obtain a FunctionType object."""
    func_type = ast.parse(type_comment, "<type_comment>", "func_type")
    return FunctionType(argtypes=func_type.argtypes, returns=func_type.returns)


UNARY_OP_CLASSES: Final[dict[type[ast.unaryop], str]] = {
    ast.UAdd: "+",
    ast.USub: "-",
    ast.Not: "not",
    ast.Invert: "~",
}

BIN_OP_CLASSES: Final[dict[type[ast.operator], str]] = {
    ast.Add: "+",
    ast.BitAnd: "&",
    ast.BitOr: "|",
    ast.BitXor: "^",
    ast.Div: "/",
    ast.FloorDiv: "//",
    ast.MatMult: "@",
    ast.Mod: "%",
    ast.Mult: "*",
    ast.Pow: "**",
    ast.Sub: "-",
    ast.LShift: "<<",
    ast.RShift: ">>",
}

BOOL_OP_CLASSES: Final[dict[type[ast.boolop], str]] = {
    ast.And: "and",
    ast.Or: "or",
}

CMP_OP_CLASSES: Final[dict[type[ast.cmpop], str]] = {
    ast.Eq: "==",
    ast.Gt: ">",
    ast.GtE: ">=",
    ast.In: "in",
    ast.Is: "is",
    ast.IsNot: "is not",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.NotEq: "!=",
    ast.NotIn: "not in",
}

CONTEXT_CLASSES: Final[dict[type[ast.expr_context], Context]] = {
    ast.Load: Context.Load,
    ast.Store: Context.Store,
    ast.Del: Context.Del,
}
