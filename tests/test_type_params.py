# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import pytest

from astroid import extract_node
from astroid.const import PY312_PLUS, PY313_PLUS
from astroid.nodes import (
    AssignName,
    List,
    Name,
    ParamSpec,
    Subscript,
    Tuple,
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
    assert node.type_params[0].default_value is None

    assert isinstance(node.value, Subscript)
    assert node.value.value.name == "list"
    assert node.value.slice.name == "tuple"
    assert all(elt.name == "float" for elt in node.value.slice.elts)

    assert node.inferred()[0] is node
    assert node.type_params[0].inferred()[0] is node.type_params[0]

    assert node.statement() is node

    assigned = next(node.assigned_stmts())
    assert assigned.qname() == "typing.TypeAliasType"


def test_type_param_spec() -> None:
    node = extract_node("type Alias[**P] = Callable[P, int]")
    params = node.type_params[0]
    assert isinstance(params, ParamSpec)
    assert isinstance(params.name, AssignName)
    assert params.name.name == "P"
    assert params.default_value is None

    assert node.inferred()[0] is node


@pytest.mark.skipif(not PY313_PLUS, reason="Type parameter defaults were added in 313")
def test_type_param_spec_defaults() -> None:
    node = extract_node("type Alias[**P = [int, str]] = Callable[P, int]")
    params = node.type_params[0]
    assert isinstance(params, ParamSpec)
    assert isinstance(params.name, AssignName)
    assert params.name.name == "P"
    assert isinstance(params.default_value, List)
    assert len(params.default_value.elts) == 2

    assert node.inferred()[0] is node


def test_type_var_tuple() -> None:
    node = extract_node("type Alias[*Ts] = tuple[*Ts]")
    params = node.type_params[0]
    assert isinstance(params, TypeVarTuple)
    assert isinstance(params.name, AssignName)
    assert params.name.name == "Ts"
    assert params.default_value is None

    assert node.inferred()[0] is node


@pytest.mark.skipif(not PY313_PLUS, reason="Type parameter defaults were added in 313")
def test_type_var_tuple_defaults() -> None:
    node = extract_node("type Alias[*Ts = tuple[int, str]] = tuple[*Ts]")
    params = node.type_params[0]
    assert isinstance(params, TypeVarTuple)
    assert isinstance(params.name, AssignName)
    assert params.name.name == "Ts"
    assert isinstance(params.default_value, Subscript)
    assert isinstance(params.default_value.value, Name)
    assert params.default_value.value.name == "tuple"
    assert isinstance(params.default_value.slice, Tuple)
    assert len(params.default_value.slice.elts) == 2

    assert node.inferred()[0] is node
