# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Tests for inference involving constraints."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from astroid import builder, nodes
from astroid.bases import Instance
from astroid.util import Uninferable


def node_info(node: nodes.NodeNG) -> str:
    return f"Inference of {node.as_string()!r} at line {node.lineno}"


def common_params(node: str) -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        ("condition", "satisfy_val", "fail_val"),
        (
            (f"{node} is None", None, 3),
            (f"{node} is not None", 3, None),
            (f"{node}", 3, None),
            (f"not {node}", None, 3),
            (f"isinstance({node}, int)", 3, None),
            (f"isinstance({node}, (int, str))", 3, None),
            (f"{node} == 3", 3, None),
            (f"{node} != 3", None, 3),
            (f"3 == {node}", 3, None),
            (f"3 != {node}", None, 3),
            (f"isinstance({node}, int) and {node} == 3", 3, 5),
            (
                f"{node} is not None and (isinstance({node}, int) and {node} == 3)",
                3,
                None,
            ),  # Nested AND
            (
                f"{node} is not None and {node} and isinstance({node}, int) and {node} == 3",
                3,
                0,
            ),  # AND with multiple constraints
            (f"isinstance({node}, str) or {node} == 3", 3, None),
            (
                f"{node} is None or (isinstance({node}, str) or {node} == 3)",
                None,
                5,
            ),  # Nested OR
            (
                f"{node} is None or not {node} or isinstance({node}, str) or {node} == 3",
                0,
                5,
            ),  # OR with multiple constraints
            (
                f"{node} is not None and (isinstance({node}, bool) or {node} == 3)",
                True,
                None,
            ),  # AND with nested OR
            (
                f"{node} is None or (isinstance({node}, bool) and {node} == 3)",
                None,
                5,
            ),  # OR with nested AND
            (
                f"{node} == 3 or isinstance({node}, int) and {node} == 5",
                3,
                None,
            ),  # AND precedence over OR
        ),
    )


@common_params(node="x")
def test_if_single_statement(
    condition: str, satisfy_val: int | None, fail_val: int | None
) -> None:
    """Test constraint for a variable that is used in the first statement of an if body."""
    node1, node2 = builder.extract_node(f"""
    def f1(x = {fail_val}):
        if {condition}:  # Filters out default value
            return (
                x  #@
            )

    def f2(x = {satisfy_val}):
        if {condition}:  # Does not filter out default value
            return (
                x  #@
            )
    """)

    inferred = node1.inferred()
    assert len(inferred) == 1
    assert inferred[0] is Uninferable

    inferred = node2.inferred()
    assert len(inferred) == 2
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == satisfy_val

    assert inferred[1] is Uninferable


@common_params(node="x")
def test_if_multiple_statements(
    condition: str, satisfy_val: int | None, fail_val: int | None
) -> None:
    """Test constraint for a variable that is used in an if body with multiple
    statements.
    """
    node1, node2 = builder.extract_node(f"""
    def f1(x = {fail_val}):
        if {condition}:  # Filters out default value
            print(x)
            return (
                x  #@
            )

    def f2(x = {satisfy_val}):
        if {condition}:  # Does not filter out default value
            print(x)
            return (
                x  #@
            )
    """)

    inferred = node1.inferred()
    assert len(inferred) == 1
    assert inferred[0] is Uninferable

    inferred = node2.inferred()
    assert len(inferred) == 2
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == satisfy_val

    assert inferred[1] is Uninferable


@common_params(node="x")
def test_if_irrelevant_condition(
    condition: str, satisfy_val: int | None, fail_val: int | None
) -> None:
    """Test that constraint for a different variable doesn't apply."""
    nodes_ = builder.extract_node(f"""
    def f1(x, y = {fail_val}):
        if {condition}:  # Does not filter out fail_val
            return (
                y  #@
            )

    def f2(x, y = {satisfy_val}):
        if {condition}:
            return (
                y  #@
            )
    """)
    for node, val in zip(nodes_, (fail_val, satisfy_val)):
        inferred = node.inferred()
        assert len(inferred) == 2
        assert isinstance(inferred[0], nodes.Const)
        assert inferred[0].value == val

        assert inferred[1] is Uninferable


@common_params(node="x")
def test_outside_if(
    condition: str, satisfy_val: int | None, fail_val: int | None
) -> None:
    """Test that constraint in an if condition doesn't apply outside of the if."""
    nodes_ = builder.extract_node(f"""
    def f1(x = {fail_val}):
        if {condition}:
            pass
        return (
            x  #@
        )

    def f2(x = {satisfy_val}):
        if {condition}:
            pass

        return (
            x  #@
        )
    """)
    for node, val in zip(nodes_, (fail_val, satisfy_val)):
        inferred = node.inferred()
        assert len(inferred) == 2
        assert isinstance(inferred[0], nodes.Const)
        assert inferred[0].value == val

        assert inferred[1] is Uninferable


@common_params(node="x")
def test_nested_if(
    condition: str, satisfy_val: int | None, fail_val: int | None
) -> None:
    """Test that constraint in an if condition applies within inner if statements."""
    node1, node2 = builder.extract_node(f"""
    def f1(y, x = {fail_val}):
        if {condition}:
            if y is not None:
                return (
                    x  #@
                )

    def f2(y, x = {satisfy_val}):
        if {condition}:
            if y is not None:
                return (
                    x  #@
                )
    """)
    inferred = node1.inferred()
    assert len(inferred) == 1
    assert inferred[0] is Uninferable

    inferred = node2.inferred()
    assert len(inferred) == 2
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == satisfy_val

    assert inferred[1] is Uninferable


def test_if_uninferable() -> None:
    """Test that when no inferred values satisfy all constraints, Uninferable is
    inferred.
    """
    node1, node2 = builder.extract_node("""
    def f1():
        x = None
        if x is not None:
            x  #@

    def f2():
        x = 1
        if x is not None:
            pass
        else:
            x  #@
    """)
    inferred = node1.inferred()
    assert len(inferred) == 1
    assert inferred[0] is Uninferable

    inferred = node2.inferred()
    assert len(inferred) == 1
    assert inferred[0] is Uninferable


@common_params(node="x")
def test_if_reassignment_in_body(
    condition: str, satisfy_val: int | None, fail_val: int | None
) -> None:
    """Test that constraint in an if condition doesn't apply when the variable
    is assigned to a failing value inside the if body.
    """
    node = builder.extract_node(f"""
    def f(x, y):
        if {condition}:
            if y:
                x = {fail_val}
            return (
                x  #@
            )
    """)
    inferred = node.inferred()
    assert len(inferred) == 2
    assert inferred[0] is Uninferable

    assert isinstance(inferred[1], nodes.Const)
    assert inferred[1].value == fail_val


@common_params(node="x")
def test_if_elif_else_negates(
    condition: str, satisfy_val: int | None, fail_val: int | None
) -> None:
    """Test that constraint in an if condition is negated when the variable
    is used in the elif and else branches.
    """
    node1, node2, node3, node4 = builder.extract_node(f"""
    def f1(y, x = {fail_val}):
        if {condition}:
            pass
        elif y:  # Does not filter out default value
            return (
                x  #@
            )
        else:  # Does not filter out default value
            return (
                x  #@
            )

    def f2(y, x = {satisfy_val}):
        if {condition}:
            pass
        elif y:  # Filters out default value
            return (
                x  #@
            )
        else:  # Filters out default value
            return (
                x  #@
            )
    """)
    for node in (node1, node2):
        msg = node_info(node)
        inferred = node.inferred()
        assert len(inferred) == 2, msg
        assert isinstance(inferred[0], nodes.Const), msg
        assert inferred[0].value == fail_val, msg

        assert inferred[1] is Uninferable, msg

    for node in (node3, node4):
        msg = node_info(node)
        inferred = node.inferred()
        assert len(inferred) == 1, msg
        assert inferred[0] is Uninferable, msg


@common_params(node="x")
def test_if_reassignment_in_else(
    condition: str, satisfy_val: int | None, fail_val: int | None
) -> None:
    """Test that constraint in an if condition doesn't apply when the variable
    is assigned to a failing value inside the else branch.
    """
    node = builder.extract_node(f"""
    def f(x, y):
        if {condition}:
            return x
        else:
            if y:
                x = {satisfy_val}
            return (
                x  #@
            )
    """)
    inferred = node.inferred()
    assert len(inferred) == 2
    assert inferred[0] is Uninferable

    assert isinstance(inferred[1], nodes.Const)
    assert inferred[1].value == satisfy_val


@common_params(node="x")
def test_if_comprehension_shadow(
    condition: str, satisfy_val: int | None, fail_val: int | None
) -> None:
    """Test that constraint in an if condition doesn't apply when the variable
    is shadowed by an inner comprehension scope.
    """
    node = builder.extract_node(f"""
    def f(x):
        if {condition}:
            return [
                x  #@
                for x in [{satisfy_val}, {fail_val}]
            ]
    """)
    inferred = node.inferred()
    assert len(inferred) == 2

    for actual, expected in zip(inferred, (satisfy_val, fail_val)):
        assert isinstance(actual, nodes.Const)
        assert actual.value == expected


@common_params(node="x")
def test_if_function_shadow(
    condition: str, satisfy_val: int | None, fail_val: int | None
) -> None:
    """Test that constraint in an if condition doesn't apply when the variable
    is shadowed by an inner function scope.
    """
    node = builder.extract_node(f"""
    x = {satisfy_val}
    if {condition}:
        def f(x = {fail_val}):
            return (
                x  #@
            )
    """)
    inferred = node.inferred()
    assert len(inferred) == 2
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == fail_val

    assert inferred[1] is Uninferable


@common_params(node="x")
def test_if_function_call(
    condition: str, satisfy_val: int | None, fail_val: int | None
) -> None:
    """Test that constraint in an if condition doesn't apply for a parameter
    a different function call, but with the same name.
    """
    node = builder.extract_node(f"""
    def f(x = {satisfy_val}):
        if {condition}:
            g({fail_val})  #@

    def g(x):
        return x
    """)
    inferred = node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == fail_val


@common_params(node="self.x")
def test_if_instance_attr(
    condition: str, satisfy_val: int | None, fail_val: int | None
) -> None:
    """Test constraint for an instance attribute in an if statement."""
    node1, node2 = builder.extract_node(f"""
    class A1:
        def __init__(self, x = {fail_val}):
            self.x = x

        def method(self):
            if {condition}:
                self.x  #@

    class A2:
        def __init__(self, x = {satisfy_val}):
            self.x = x

        def method(self):
            if {condition}:
                self.x  #@
    """)

    inferred = node1.inferred()
    assert len(inferred) == 1
    assert inferred[0] is Uninferable

    inferred = node2.inferred()
    assert len(inferred) == 2
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == satisfy_val

    assert inferred[1] is Uninferable


@common_params(node="self.x")
def test_if_instance_attr_reassignment_in_body(
    condition: str, satisfy_val: int | None, fail_val: int | None
) -> None:
    """Test that constraint in an if condition doesn't apply to an instance attribute
    when it is assigned inside the if body.
    """
    node1, node2 = builder.extract_node(f"""
    class A1:
        def __init__(self, x):
            self.x = x

        def method1(self):
            if {condition}:
                self.x = {satisfy_val}
                self.x  #@

        def method2(self):
            if {condition}:
                self.x = {fail_val}
                self.x  #@
    """)

    inferred = node1.inferred()
    assert len(inferred) == 2
    assert inferred[0] is Uninferable

    assert isinstance(inferred[1], nodes.Const)
    assert inferred[1].value == satisfy_val

    inferred = node2.inferred()
    assert len(inferred) == 3
    assert inferred[0] is Uninferable

    assert isinstance(inferred[1], nodes.Const)
    assert inferred[1].value == satisfy_val

    assert isinstance(inferred[2], nodes.Const)
    assert inferred[2].value == fail_val


@common_params(node="x")
def test_if_instance_attr_varname_collision1(
    condition: str, satisfy_val: int | None, fail_val: int | None
) -> None:
    """Test that constraint in an if condition doesn't apply to an instance attribute
    when the constraint refers to a variable with the same name.
    """
    node1, node2 = builder.extract_node(f"""
    class A1:
        def __init__(self, x = {fail_val}):
            self.x = x

        def method(self, x = {fail_val}):
            if {condition}:
                x  #@
                self.x  #@
    """)

    inferred = node1.inferred()
    assert len(inferred) == 1
    assert inferred[0] is Uninferable

    inferred = node2.inferred()
    assert len(inferred) == 2
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == fail_val

    assert inferred[1] is Uninferable


@common_params(node="self.x")
def test_if_instance_attr_varname_collision2(
    condition: str, satisfy_val: int | None, fail_val: int | None
) -> None:
    """Test that constraint in an if condition doesn't apply to a variable with the same
    name.
    """
    node1, node2 = builder.extract_node(f"""
    class A1:
        def __init__(self, x = {fail_val}):
            self.x = x

        def method(self, x = {fail_val}):
            if {condition}:
                x  #@
                self.x  #@
    """)

    inferred = node1.inferred()
    assert len(inferred) == 2
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == fail_val

    assert inferred[1] is Uninferable

    inferred = node2.inferred()
    assert len(inferred) == 1
    assert inferred[0] is Uninferable


@common_params(node="self.x")
def test_if_instance_attr_varname_collision3(
    condition: str, satisfy_val: int | None, fail_val: int | None
) -> None:
    """Test that constraint in an if condition doesn't apply to an instance attribute
    for an object of a different class.
    """
    node = builder.extract_node(f"""
    class A1:
        def __init__(self, x = {fail_val}):
            self.x = x

        def method(self):
            obj = A2()
            if {condition}:
                obj.x  #@

    class A2:
        def __init__(self):
            self.x = {fail_val}
    """)

    inferred = node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == fail_val


@common_params(node="self.x")
def test_if_instance_attr_varname_collision4(
    condition: str, satisfy_val: int | None, fail_val: int | None
) -> None:
    """Test that constraint in an if condition doesn't apply to a variable of the same name,
    when that variable is used to infer the value of the instance attribute.
    """
    node = builder.extract_node(f"""
    class A1:
        def __init__(self, x):
            self.x = x

        def method(self):
            x = {fail_val}
            if {condition}:
                self.x = x
                self.x  #@
    """)

    inferred = node.inferred()
    assert len(inferred) == 2
    assert inferred[0] is Uninferable

    assert isinstance(inferred[1], nodes.Const)
    assert inferred[1].value == fail_val


@common_params(node="x")
def test_if_exp_body(
    condition: str, satisfy_val: int | None, fail_val: int | None
) -> None:
    """Test constraint for a variable that is used in an if exp body."""
    node1, node2 = builder.extract_node(f"""
    def f1(x = {fail_val}):
        return (
            x if {condition} else None  #@
        )

    def f2(x = {satisfy_val}):
        return (
            x if {condition} else None  #@
        )
    """)

    inferred = node1.body.inferred()
    assert len(inferred) == 1
    assert inferred[0] is Uninferable

    inferred = node2.body.inferred()
    assert len(inferred) == 2
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == satisfy_val
    assert inferred[1] is Uninferable


@common_params(node="x")
def test_if_exp_else(
    condition: str, satisfy_val: int | None, fail_val: int | None
) -> None:
    """Test constraint for a variable that is used in an if exp else block."""
    node1, node2 = builder.extract_node(f"""
    def f1(x = {satisfy_val}):
        return (
            None if {condition} else x  #@
        )

    def f2(x = {fail_val}):
        return (
            None if {condition} else x  #@
        )
    """)

    inferred = node1.orelse.inferred()
    assert len(inferred) == 1
    assert inferred[0] is Uninferable

    inferred = node2.orelse.inferred()
    assert len(inferred) == 2
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == fail_val
    assert inferred[1] is Uninferable


@common_params(node="x")
def test_outside_if_exp(
    condition: str, satisfy_val: int | None, fail_val: int | None
) -> None:
    """Test that constraint in an if exp condition doesn't apply outside of the if exp."""
    nodes_ = builder.extract_node(f"""
    def f1(x = {fail_val}):
        x if {condition} else None
        return (
            x  #@
        )

    def f2(x = {satisfy_val}):
        None if {condition} else x
        return (
            x  #@
        )
    """)
    for node, val in zip(nodes_, (fail_val, satisfy_val)):
        inferred = node.inferred()
        assert len(inferred) == 2
        assert isinstance(inferred[0], nodes.Const)
        assert inferred[0].value == val
        assert inferred[1] is Uninferable


@common_params(node="x")
def test_nested_if_exp(
    condition: str, satisfy_val: int | None, fail_val: int | None
) -> None:
    """Test that constraint in an if exp condition applies within inner if exp."""
    node1, node2 = builder.extract_node(f"""
    def f1(y, x = {fail_val}):
        return (
            (x if y else None) if {condition} else None  #@
        )

    def f2(y, x = {satisfy_val}):
        return (
            (x if y else None) if {condition} else None  #@
        )
    """)

    inferred = node1.body.body.inferred()
    assert len(inferred) == 1
    assert inferred[0] is Uninferable

    inferred = node2.body.body.inferred()
    assert len(inferred) == 2
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == satisfy_val
    assert inferred[1] is Uninferable


@common_params(node="self.x")
def test_if_exp_instance_attr(
    condition: str, satisfy_val: int | None, fail_val: int | None
) -> None:
    """Test constraint for an instance attribute in an if exp."""
    node1, node2 = builder.extract_node(f"""
    class A1:
        def __init__(self, x = {fail_val}):
            self.x = x

        def method(self):
            return (
                self.x if {condition} else None  #@
            )

    class A2:
        def __init__(self, x = {satisfy_val}):
            self.x = x

        def method(self):
            return (
                self.x if {condition} else None  #@
            )
    """)

    inferred = node1.body.inferred()
    assert len(inferred) == 1
    assert inferred[0] is Uninferable

    inferred = node2.body.inferred()
    assert len(inferred) == 2
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == satisfy_val
    assert inferred[1].value is Uninferable


@common_params(node="self.x")
def test_if_exp_instance_attr_varname_collision(
    condition: str, satisfy_val: int | None, fail_val: int | None
) -> None:
    """Test that constraint in an if exp condition doesn't apply to a variable with the same name."""
    node = builder.extract_node(f"""
    class A:
        def __init__(self, x = {fail_val}):
            self.x = x

        def method(self, x = {fail_val}):
            return (
                x if {condition} else None  #@
            )
    """)

    inferred = node.body.inferred()
    assert len(inferred) == 2
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == fail_val
    assert inferred[1].value is Uninferable


def test_isinstance_equal_types() -> None:
    """Test constraint for an object whose type is equal to the checked type."""
    node = builder.extract_node("""
    class A:
        pass

    x = A()

    if isinstance(x, A):
        x  #@
    """)

    inferred = node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], Instance)
    assert isinstance(inferred[0]._proxied, nodes.ClassDef)
    assert inferred[0].name == "A"


def test_isinstance_subtype() -> None:
    """Test constraint for an object whose type is a strict subtype of the checked type."""
    node = builder.extract_node("""
    class A:
        pass

    class B(A):
        pass

    x = B()

    if isinstance(x, A):
        x  #@
    """)

    inferred = node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], Instance)
    assert isinstance(inferred[0]._proxied, nodes.ClassDef)
    assert inferred[0].name == "B"


def test_isinstance_unrelated_types():
    """Test constraint for an object whose type is not related to the checked type."""
    node = builder.extract_node("""
    class A:
        pass

    class B:
        pass

    x = A()

    if isinstance(x, B):
        x  #@
    """)

    inferred = node.inferred()
    assert len(inferred) == 1
    assert inferred[0] is Uninferable


def test_isinstance_supertype():
    """Test constraint for an object whose type is a strict supertype of the checked type."""
    node = builder.extract_node("""
    class A:
        pass

    class B(A):
        pass

    x = A()

    if isinstance(x, B):
        x  #@
    """)

    inferred = node.inferred()
    assert len(inferred) == 1
    assert inferred[0] is Uninferable


def test_isinstance_multiple_inheritance():
    """Test constraint for an object that inherits from more than one parent class."""
    n1, n2, n3 = builder.extract_node("""
    class A:
        pass

    class B:
        pass

    class C(A, B):
        pass

    x = C()

    if isinstance(x, C):
        x  #@

    if isinstance(x, A):
        x  #@

    if isinstance(x, B):
        x  #@
    """)

    for node in (n1, n2, n3):
        msg = node_info(node)
        inferred = node.inferred()
        assert len(inferred) == 1, msg
        assert isinstance(inferred[0], Instance), msg
        assert isinstance(inferred[0]._proxied, nodes.ClassDef), msg
        assert inferred[0].name == "C", msg


def test_isinstance_diamond_inheritance():
    """Test constraint for an object that inherits from parent classes
    in diamond inheritance.
    """
    n1, n2, n3, n4 = builder.extract_node("""
    class A():
        pass

    class B(A):
        pass

    class C(A):
        pass

    class D(B, C):
        pass

    x = D()

    if isinstance(x, D):
        x  #@

    if isinstance(x, B):
        x  #@

    if isinstance(x, C):
        x  #@

    if isinstance(x, A):
        x  #@
    """)

    for node in (n1, n2, n3, n4):
        msg = node_info(node)
        inferred = node.inferred()
        assert len(inferred) == 1, msg
        assert isinstance(inferred[0], Instance), msg
        assert isinstance(inferred[0]._proxied, nodes.ClassDef), msg
        assert inferred[0].name == "D", msg


def test_isinstance_keyword_arguments():
    """Test that constraint does not apply when `isinstance` is called
    with keyword arguments.
    """
    n1, n2 = builder.extract_node("""
    x = 3

    if isinstance(object=x, classinfo=str):
        x  #@

    if isinstance(x, str, object=x, classinfo=str):
        x  #@
    """)

    for node in (n1, n2):
        msg = node_info(node)
        inferred = node.inferred()
        assert len(inferred) == 1, msg
        assert isinstance(inferred[0], nodes.Const), msg
        assert inferred[0].value == 3, msg


def test_isinstance_extra_argument():
    """Test that constraint does not apply when `isinstance` is called
    with more than two positional arguments.
    """
    node = builder.extract_node("""
    x = 3

    if isinstance(x, str, bool):
        x  #@
    """)

    inferred = node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == 3


def test_isinstance_classinfo_inference_error():
    """Test that constraint is satisfied when `isinstance` is called with
    classinfo that raises an inference error.
    """
    node = builder.extract_node("""
    x = 3

    if isinstance(x, undefined_type):
        x  #@
    """)

    inferred = node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == 3


def test_isinstance_uninferable_classinfo():
    """Test that constraint is satisfied when `isinstance` is called with
    uninferable classinfo.
    """
    node = builder.extract_node("""
    def f(classinfo):
        x = 3

        if isinstance(x, classinfo):
            x  #@
    """)

    inferred = node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == 3


def test_isinstance_mro_error():
    """Test that constraint is satisfied when computing the object's
    method resolution order raises an MRO error.
    """
    node = builder.extract_node("""
    class A():
        pass

    class B(A, A):
        pass

    x = B()

    if isinstance(x, A):
        x  #@
    """)

    inferred = node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], Instance)
    assert isinstance(inferred[0]._proxied, nodes.ClassDef)
    assert inferred[0].name == "B"


def test_isinstance_uninferable():
    """Test that constraint is satisfied when `isinstance` inference returns Uninferable."""
    node = builder.extract_node("""
    x = 3

    if isinstance(x, str):
        x  #@
    """)

    with patch(
        "astroid.constraint.helpers.object_isinstance", return_value=Uninferable
    ):
        inferred = node.inferred()
        assert len(inferred) == 1
        assert isinstance(inferred[0], nodes.Const)
        assert inferred[0].value == 3


def test_equality_callable():
    """Test constraint for equality of callables."""
    node1, node2, node3, node4, node5, node6 = builder.extract_node("""
    class Foo:
        pass

    def bar():
        pass

    baz = lambda i : i

    x, y, z = Foo, bar, baz

    if x == Foo:
        x  #@
    if x != Foo:
        x  #@

    if y == bar:
        y  #@
    if y != bar:
        y  #@

    if z == baz:
        z  #@
    if z != baz:
        z  #@
    """)

    inferred = node1.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.ClassDef)
    assert inferred[0].name == "Foo"

    inferred = node3.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.FunctionDef)
    assert inferred[0].name == "bar"

    inferred = node5.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.Lambda)

    for node in (node2, node4, node6):
        msg = node_info(node)
        inferred = node.inferred()
        assert len(inferred) == 1, msg
        assert inferred[0] is Uninferable, msg


def test_equality_uninferable_operand():
    """Test that equality constraint is satisfied when either operand is uninferable."""
    node1, node2, node3, node4 = builder.extract_node("""
    def f1(x):
        if x == 3:
            x  #@

        if x != 3:
            x  #@

    def f2(y):
        x = 3
        if x == y:
            x  #@

        if x != y:
            x  #@
    """)

    for node in (node1, node2):
        msg = node_info(node)
        inferred = node.inferred()
        assert len(inferred) == 1, msg
        assert inferred[0] is Uninferable, msg

    for node in (node3, node4):
        msg = node_info(node)
        inferred = node.inferred()
        assert len(inferred) == 1, msg
        assert isinstance(inferred[0], nodes.Const), msg
        assert inferred[0].value == 3, msg


def test_equality_ambiguous_operand():
    """Test that equality constraint is satisfied when the compared operand has multiple inferred values."""
    node1, node2 = builder.extract_node("""
    def f(y = 1):
        x = 3
        if x == y:
            x  #@

        if x != y:
            x  #@
    """)

    for node in (node1, node2):
        msg = node_info(node)
        inferred = node.inferred()
        assert len(inferred) == 1, msg
        assert isinstance(inferred[0], nodes.Const), msg
        assert inferred[0].value == 3, msg


def test_equality_fractions():
    """Test that equality constraint is satisfied when both operands are fractions."""
    node1, node2, node3, node4 = builder.extract_node("""
    from fractions import Fraction

    x = Fraction(1, 3)
    y = Fraction(1, 3)

    if x == y:
        x  #@
        y  #@

    if x != y:
        x  #@
        y  #@
    """)

    for node in (node1, node2, node3, node4):
        msg = node_info(node)
        inferred = node.inferred()
        assert len(inferred) == 1, msg
        assert isinstance(inferred[0], Instance), msg
        assert isinstance(inferred[0]._proxied, nodes.ClassDef), msg
        assert inferred[0]._proxied.name == "Fraction", msg


def test_and_expression_with_non_constraint():
    """Test that constraint is satisfied when an "and" expression contains a non-constraint operand."""
    node = builder.extract_node("""
    x, y = 3, None

    if not x and y:
        x  #@
    """)

    inferred = node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == 3


def test_and_expression_with_nested_non_constraint():
    """Test that constraint is satisfied when a nested "and" expression contains a non-constraint operand."""
    node = builder.extract_node("""
    x, y = 3, None

    if x is not None and (not x and y):
        x  #@
    """)

    inferred = node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == 3


def test_or_expression_with_non_constraint():
    """Test that constraint is satisfied when an "or" expression contains a non-constraint operand."""
    node = builder.extract_node("""
    x, y = 3, None

    if not x or y:
        x  #@
    """)

    inferred = node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == 3


def test_or_expression_with_nested_non_constraint():
    """Test that constraint is satisfied when a nested "or" expression contains a non-constraint operand."""
    node = builder.extract_node("""
    x, y = 3, None

    if x is None or (not x or y):
        x  #@
    """)

    inferred = node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == 3
