import ast

_ast_py2 = _ast_py3 = None
try:
    import typed_ast.ast3 as _ast_py3
    import typed_ast.ast27 as _ast_py2
except ImportError:
    pass


def _get_parser_module(parse_python_two: bool = False):
    if parse_python_two:
        parser_module = _ast_py2
    else:
        parser_module = _ast_py3
    return parser_module or ast


def _parse(string: str,
           parse_python_two: bool = False):
    return _get_parser_module(parse_python_two=parse_python_two).parse(string)
