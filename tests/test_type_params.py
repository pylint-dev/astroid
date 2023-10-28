# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import pytest

from astroid import extract_node
from astroid.const import PY312_PLUS
from astroid.nodes import (
    AssignName,
    ParamSpec,
    Subscript,
    TypeAlias,
    TypeVar,
    TypeVarTuple,
)

if not PY312_PLUS:
    pytest.skip("Requires Python 3.12 or higher", allow_module_level=True)


def test_type_alias() -> None:
    node = extract_node("type Point[T] = list[float, float]")
    assert isinstance(node, TypeAlias)
    assert isinstance(node.type_params[0], TypeVar)
    assert isinstance(node.type_params[0].name, AssignName)
    assert node.type_params[0].name.name == "T"
    assert node.type_params[0].bound is None

    assert isinstance(node.value, Subscript)
    assert node.value.value.name == "list"
    assert node.value.slice.name == "tuple"
    assert all(elt.name == "float" for elt in node.value.slice.elts)

    assert node.inferred()[0] is node
    assert node.type_params[0].inferred()[0] is node.type_params[0]

    assert node.statement() is node

    assigned = next(node.assigned_stmts())
    assert assigned is node.value


def test_type_param_spec() -> None:
    node = extract_node("type Alias[**P] = Callable[P, int]")
    params = node.type_params[0]
    assert isinstance(params, ParamSpec)
    assert isinstance(params.name, AssignName)
    assert params.name.name == "P"

    assert node.inferred()[0] is node


def test_type_var_tuple() -> None:
    node = extract_node("type Alias[*Ts] = tuple[*Ts]")
    params = node.type_params[0]
    assert isinstance(params, TypeVarTuple)
    assert isinstance(params.name, AssignName)
    assert params.name.name == "Ts"

    assert node.inferred()[0] is node


def test_type_param() -> None:
    func_node = extract_node("def func[T]() -> T: ...")
    assert isinstance(func_node.type_params[0], TypeVar)
    assert func_node.type_params[0].name.name == "T"
    assert func_node.type_params[0].bound is None

    class_node = extract_node("class MyClass[T]: ...")
    assert isinstance(class_node.type_params[0], TypeVar)
    assert class_node.type_params[0].name.name == "T"
    assert class_node.type_params[0].bound is None


def test_get_children() -> None:
    func_node = extract_node("def func[T]() -> T: ...")
    func_children = tuple(func_node.get_children())
    assert isinstance(func_children[2], TypeVar)

    class_node = extract_node("class MyClass[T]: ...")
    class_children = tuple(class_node.get_children())
    assert isinstance(class_children[0], TypeVar)
