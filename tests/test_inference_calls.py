# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Tests for function call inference."""

from astroid import bases, builder, nodes


def test_multiple_returns() -> None:
    """Test function with multiple returns."""
    node = builder.extract_node("""
    def f(x):
        if x > 10:
            return 1
        elif x > 20:
            return 2
        else:
            return 3

    f(100)  #@
    """)
    assert isinstance(node, nodes.NodeNG)
    inferred = node.inferred()
    assert len(inferred) == 3
    assert all(isinstance(node, nodes.Const) for node in inferred)
    assert {node.value for node in inferred} == {1, 2, 3}


def test_method_const_instance_attr_multiple() -> None:
    """Test method where the return value is based on an instance attribute with
    multiple possible constant values, across different methods.
    """
    node = builder.extract_node("""
    class A:
        def __init__(self, x):
            if x:
                self.x = 1
            else:
                self.x = 2

        def set_x(self):
            self.x = 3

        def get_x(self):
            return self.x

    A().get_x()  #@
    """)
    assert isinstance(node, nodes.NodeNG)
    inferred = node.inferred()
    assert len(inferred) == 3
    assert all(isinstance(node, nodes.Const) for node in inferred)
    assert {node.value for node in inferred} == {1, 2, 3}


def test_method_const_instance_attr_same_method() -> None:
    """Test method where the return value is based on an instance attribute with
    multiple possible constant values, including in the method being called.

    Note that even with a simple control flow where the assignment in the method body
    is guaranteed to override any previous assignments, all possible constant values
    are returned.
    """
    node = builder.extract_node("""
    class A:
        def __init__(self, x):
            if x:
                self.x = 1
            else:
                self.x = 2

        def set_x(self):
            self.x = 3

        def get_x(self):
            self.x = 4
            return self.x

    A().get_x()  #@
    """)
    assert isinstance(node, nodes.NodeNG)
    inferred = node.inferred()
    assert len(inferred) == 4
    assert all(isinstance(node, nodes.Const) for node in inferred)
    assert {node.value for node in inferred} == {1, 2, 3, 4}


def test_instance_method_inherited() -> None:
    """Tests for instance methods that are inherited from a superclass.

    Based on https://github.com/pylint-dev/astroid/issues/1008.
    """
    nodes_ = builder.extract_node("""
    class A:
        def method(self):
            return self

    class B(A):
        pass

    A().method()  #@
    A.method(A())  #@

    B().method()  #@
    B.method(B())  #@
    A.method(B())  #@
    """)
    expected_names = ["A", "A", "B", "B", "B"]
    for node, expected in zip(nodes_, expected_names):
        assert isinstance(node, nodes.NodeNG)
        inferred = node.inferred()
        assert len(inferred) == 1
        assert isinstance(inferred[0], bases.Instance)
        assert inferred[0].name == expected


def test_class_method_inherited() -> None:
    """Tests for class methods that are inherited from a superclass.

    Based on https://github.com/pylint-dev/astroid/issues/1008.
    """
    nodes_ = builder.extract_node("""
    class A:
        @classmethod
        def method(cls):
            return cls

    class B(A):
        pass

    A().method()  #@
    A.method()  #@

    B().method()  #@
    B.method()  #@
    """)
    expected_names = ["A", "A", "B", "B"]
    for node, expected in zip(nodes_, expected_names):
        assert isinstance(node, nodes.NodeNG)
        inferred = node.inferred()
        assert len(inferred) == 1
        assert isinstance(inferred[0], nodes.ClassDef)
        assert inferred[0].name == expected
