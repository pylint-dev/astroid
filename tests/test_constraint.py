# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Tests for inference involving constraints."""
from __future__ import annotations

import pytest

from astroid import builder, nodes
from astroid.util import Uninferable


def common_params(node: str) -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        ("condition", "satisfy_val", "fail_val"),
        (
            (f"{node} is None", None, 3),
            (f"{node} is not None", 3, None),
        ),
    )


@common_params(node="x")
def test_if_single_statement(
    condition: str, satisfy_val: int | None, fail_val: int | None
) -> None:
    """Test constraint for a variable that is used in the first statement of an if body."""
    node1, node2 = builder.extract_node(
        f"""
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
    """
    )

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
    node1, node2 = builder.extract_node(
        f"""
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
    """
    )

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
    nodes_ = builder.extract_node(
        f"""
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
    """
    )
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
    nodes_ = builder.extract_node(
        f"""
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
    """
    )
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
    node1, node2 = builder.extract_node(
        f"""
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
    """
    )
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
    node1, node2 = builder.extract_node(
        """
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
    """
    )
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
    node = builder.extract_node(
        f"""
    def f(x, y):
        if {condition}:
            if y:
                x = {fail_val}
            return (
                x  #@
            )
    """
    )
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
    node1, node2, node3, node4 = builder.extract_node(
        f"""
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
    """
    )
    for node in (node1, node2):
        inferred = node.inferred()
        assert len(inferred) == 2
        assert isinstance(inferred[0], nodes.Const)
        assert inferred[0].value == fail_val

        assert inferred[1] is Uninferable

    for node in (node3, node4):
        inferred = node.inferred()
        assert len(inferred) == 1
        assert inferred[0] is Uninferable


@common_params(node="x")
def test_if_reassignment_in_else(
    condition: str, satisfy_val: int | None, fail_val: int | None
) -> None:
    """Test that constraint in an if condition doesn't apply when the variable
    is assigned to a failing value inside the else branch.
    """
    node = builder.extract_node(
        f"""
    def f(x, y):
        if {condition}:
            return x
        else:
            if y:
                x = {satisfy_val}
            return (
                x  #@
            )
    """
    )
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
    node = builder.extract_node(
        f"""
    def f(x):
        if {condition}:
            return [
                x  #@
                for x in [{satisfy_val}, {fail_val}]
            ]
    """
    )
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
    node = builder.extract_node(
        f"""
    x = {satisfy_val}
    if {condition}:
        def f(x = {fail_val}):
            return (
                x  #@
            )
    """
    )
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
    node = builder.extract_node(
        f"""
    def f(x = {satisfy_val}):
        if {condition}:
            g({fail_val})  #@

    def g(x):
        return x
    """
    )
    inferred = node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == fail_val


@common_params(node="self.x")
def test_if_instance_attr(
    condition: str, satisfy_val: int | None, fail_val: int | None
) -> None:
    """Test constraint for an instance attribute in an if statement."""
    node1, node2 = builder.extract_node(
        f"""
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
    """
    )

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
    node1, node2 = builder.extract_node(
        f"""
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
    """
    )

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
    node1, node2 = builder.extract_node(
        f"""
    class A1:
        def __init__(self, x = {fail_val}):
            self.x = x

        def method(self, x = {fail_val}):
            if {condition}:
                x  #@
                self.x  #@
    """
    )

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
    node1, node2 = builder.extract_node(
        f"""
    class A1:
        def __init__(self, x = {fail_val}):
            self.x = x

        def method(self, x = {fail_val}):
            if {condition}:
                x  #@
                self.x  #@
    """
    )

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
    node = builder.extract_node(
        f"""
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
    """
    )

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
    node = builder.extract_node(
        f"""
    class A1:
        def __init__(self, x):
            self.x = x

        def method(self):
            x = {fail_val}
            if {condition}:
                self.x = x
                self.x  #@
    """
    )

    inferred = node.inferred()
    assert len(inferred) == 2
    assert inferred[0] is Uninferable

    assert isinstance(inferred[1], nodes.Const)
    assert inferred[1].value == fail_val
