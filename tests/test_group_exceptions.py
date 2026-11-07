# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt
import textwrap

import pytest

from astroid import (
    Uninferable,
    bases,
    extract_node,
    nodes,
)
from astroid.context import InferenceContext
from astroid.util import safe_infer


@pytest.mark.parametrize(
    ("group_type", "exception_type"),
    [("ExceptionGroup", "TypeError"), ("BaseExceptionGroup", "KeyboardInterrupt")],
)
def test_group_exceptions_exceptions(group_type: str, exception_type: str) -> None:
    node = extract_node(textwrap.dedent(f"""
        try:
            raise {group_type}("group", [{exception_type}()])
        except {group_type} as eg:
            eg.exceptions #@"""))

    inferred = node.inferred()[0]
    assert inferred.pytype() == "builtins.tuple"
    assert inferred.bool_value() is Uninferable


@pytest.mark.parametrize(
    ("group_type", "exception_type"),
    [("ExceptionGroup", "TypeError"), ("BaseExceptionGroup", "KeyboardInterrupt")],
)
@pytest.mark.parametrize("operation", ["len", "bool"])
def test_group_exceptions_unknown_contents(
    group_type: str, exception_type: str, operation: str
) -> None:
    node = extract_node(textwrap.dedent(f"""
        try:
            raise {group_type}("group", [{exception_type}()])
        except {group_type} as eg:
            {operation}(eg.exceptions) #@"""))

    assert safe_infer(node) in (None, Uninferable)


def test_group_exceptions() -> None:
    node = extract_node(textwrap.dedent("""
        try:
            raise ExceptionGroup("group", [ValueError(654)])
        except ExceptionGroup as eg:
            for err in eg.exceptions:
                if isinstance(err, ValueError):
                    print("Handling ValueError")
                elif isinstance(err, TypeError):
                    print("Handling TypeError")"""))
    assert isinstance(node, nodes.Try)
    handler = node.handlers[0]
    assert node.block_range(lineno=1) == (1, 9)
    assert node.block_range(lineno=2) == (2, 3)
    assert node.block_range(lineno=5) == (5, 9)
    assert isinstance(handler, nodes.ExceptHandler)
    assert handler.type.name == "ExceptionGroup"
    children = list(handler.get_children())
    assert len(children) == 3
    exception_group, short_name, for_loop = children
    assert isinstance(exception_group, nodes.Name)
    assert exception_group.block_range(1) == (1, 4)
    assert isinstance(short_name, nodes.AssignName)
    assert isinstance(for_loop, nodes.For)


def test_star_exceptions() -> None:
    code = textwrap.dedent("""
    try:
        raise ExceptionGroup("group", [ValueError(654)])
    except* ValueError:
        print("Handling ValueError")
    except* TypeError:
        print("Handling TypeError")
    else:
        sys.exit(127)
    finally:
        sys.exit(0)""")
    node = extract_node(code)
    assert isinstance(node, nodes.TryStar)
    assert node.as_string() == code.replace('"', "'").strip()
    assert isinstance(node.body[0], nodes.Raise)
    assert node.block_range(1) == (1, 11)
    assert node.block_range(2) == (2, 3)
    assert node.block_range(3) == (3, 3)
    assert node.block_range(4) == (4, 5)
    assert node.block_range(5) == (5, 5)
    assert node.block_range(6) == (6, 7)
    assert node.block_range(7) == (7, 7)
    assert node.block_range(8) == (8, 9)
    assert node.block_range(9) == (9, 9)
    assert node.block_range(10) == (10, 11)
    assert node.block_range(11) == (11, 11)
    assert node.handlers
    handler = node.handlers[0]
    assert isinstance(handler, nodes.ExceptHandler)
    assert handler.type.name == "ValueError"
    orelse = node.orelse[0]
    assert isinstance(orelse, nodes.Expr)
    assert orelse.value.args[0].value == 127
    final = node.finalbody[0]
    assert isinstance(final, nodes.Expr)
    assert final.value.args[0].value == 0


def test_star_exceptions_infer_name() -> None:
    trystar = extract_node("""
try:
    1/0
except* ValueError:
    pass""")
    name = "arbitraryName"
    context = InferenceContext()
    context.lookupname = name
    stmts = bases._infer_stmts([trystar], context)
    assert list(stmts) == [Uninferable]
    assert context.lookupname == name


def test_star_exceptions_infer_exceptions() -> None:
    code = textwrap.dedent("""
    try:
        raise ExceptionGroup("group", [ValueError(654), TypeError(10)])
    except* ValueError as ve:
        print(e.exceptions)
    except* TypeError as te:
        print(e.exceptions)
    else:
        sys.exit(127)
    finally:
        sys.exit(0)""")
    node = extract_node(code)
    assert isinstance(node, nodes.TryStar)
    inferred_ve = next(node.handlers[0].statement().name.infer())
    assert inferred_ve.name == "ExceptionGroup"
    assert isinstance(inferred_ve.getattr("exceptions")[0], nodes.Tuple)
    assert (
        inferred_ve.getattr("exceptions")[0].elts[0].pytype() == "builtins.ValueError"
    )

    inferred_te = next(node.handlers[1].statement().name.infer())
    assert inferred_te.name == "ExceptionGroup"
    assert isinstance(inferred_te.getattr("exceptions")[0], nodes.Tuple)
    assert inferred_te.getattr("exceptions")[0].elts[0].pytype() == "builtins.TypeError"
