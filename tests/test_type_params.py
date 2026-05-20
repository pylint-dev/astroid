# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import pytest

from astroid import bases, extract_node, nodes, util
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
from astroid.protocols import _annotation_for_argname

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
    assert assigned is node.value


def test_type_var() -> None:
    node = extract_node("type Point[T: int] = T")
    param = node.type_params[0]
    assert isinstance(param, TypeVar)
    assert isinstance(param.bound, Name)
    assert param.bound.name == "int"
    assert param.default_value is None


@pytest.mark.skipif(not PY313_PLUS, reason="Type parameter defaults were added in 313")
def test_type_var_defaults() -> None:
    node = extract_node("type Point[T: int = int] = T")
    param = node.type_params[0]
    assert isinstance(param, TypeVar)
    assert isinstance(param.bound, Name)
    assert param.bound.name == "int"
    assert isinstance(param.default_value, Name)
    assert param.default_value.name == "int"


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


def test_type_var_bound_resolves_to_instance() -> None:
    """A PEP 695 TypeVar with a bound infers to an instance of the bound."""

    node = extract_node(
        """
def f[T: str](x: T) -> T:
    return x  #@
"""
    )
    inferred = list(node.value.inferred())
    assert len(inferred) == 1
    assert isinstance(inferred[0], bases.Instance)
    assert inferred[0]._proxied.name == "str"


def test_type_var_without_bound_stays_uninferable() -> None:
    """Unbounded TypeVars do not drive parameter inference."""

    node = extract_node(
        """
def f[T](x: T) -> T:
    return x  #@
"""
    )
    inferred = list(node.value.inferred())
    assert any(value is util.Uninferable for value in inferred)


def test_type_var_bound_member_lookup() -> None:
    """Members of the bound type resolve on the TypeVar-typed expression."""

    node = extract_node(
        """
def f[T: str](x: T) -> T:
    return x.upper()  #@
"""
    )
    inferred = list(node.value.inferred())
    assert len(inferred) == 1
    assert isinstance(inferred[0], bases.Instance)
    assert inferred[0]._proxied.name == "str"


def test_plain_class_annotation_does_not_drive_inference() -> None:
    """Plain annotations (``x: str``) do NOT make ``x`` infer to ``str()`` —
    annotation-driven inference is restricted to PEP 695 TypeVar bounds."""

    node = extract_node(
        """
def f(x: str) -> str:
    return x  #@
"""
    )
    inferred = list(node.value.inferred())
    assert any(value is util.Uninferable for value in inferred)


def test_unannotated_parameter_stays_uninferable() -> None:
    """A parameter without an annotation falls through with no annotation
    fallback. Covers ``_annotation_for_argname`` returning ``None`` when
    the named parameter has no annotation."""

    node = extract_node(
        """
def f[T: str](x: T, y) -> T:
    return y  #@
"""
    )
    inferred = list(node.value.inferred())
    assert any(value is util.Uninferable for value in inferred)


def test_unresolvable_bound_yields_const_placeholder() -> None:
    """If a TypeVar's bound cannot be resolved to a class, the type
    parameter still yields the historical ``Const(None)`` placeholder
    instead of crashing."""

    func = extract_node(
        """
def f[T: Undefined](x: T) -> T: ...
"""
    )
    type_param = func.type_params[0]
    inferred = list(type_param.name.inferred())
    assert any(isinstance(value, nodes.Const) for value in inferred)


def test_annotation_for_argname_returns_none_for_none_name() -> None:
    """Defensive: passing ``name=None`` to the annotation lookup helper
    returns ``None`` without scanning. Covers the guard against malformed
    call sites that would otherwise pass through to ``param.name == None``
    comparisons."""

    func = extract_node("def f[T: str](x: T) -> T: ...")
    assert _annotation_for_argname(func.args, None) is None


def test_annotation_for_argname_returns_none_when_no_match() -> None:
    """If the requested argument name does not match any parameter on
    the ``Arguments`` node, the helper returns ``None``."""

    func = extract_node("def f[T: str](x: T) -> T: ...")
    assert _annotation_for_argname(func.args, "not_a_param") is None
