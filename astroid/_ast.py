import ast
from collections import namedtuple
from typing import Optional

_ast_py2 = _ast_py3 = None
try:
    import typed_ast.ast3 as _ast_py3
    import typed_ast.ast27 as _ast_py2
except ImportError:
    pass


FunctionType = namedtuple("FunctionType", ["argtypes", "returns"])


def _get_parser_module(parse_python_two: bool = False):
    if parse_python_two:
        parser_module = _ast_py2
    else:
        parser_module = _ast_py3
    return parser_module or ast


def _parse(string: str, parse_python_two: bool = False):
    return _get_parser_module(parse_python_two=parse_python_two).parse(string)


def parse_function_type_comment(type_comment: str) -> Optional[FunctionType]:
    """Given a correct type comment, obtain a FunctionType object"""
    if _ast_py3 is None:
        return None

    func_type = _ast_py3.parse(type_comment, "<type_comment>", "func_type")
    return FunctionType(argtypes=func_type.argtypes, returns=func_type.returns)
