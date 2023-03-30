# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Tests for function call inference."""

from astroid import bases, builder, nodes
from astroid.util import Uninferable


def test_no_return() -> None:
    """Test function with no return statements."""
    node = builder.extract_node(
        """
    def f():
        pass

    f()  #@
    """
    )
    assert isinstance(node, nodes.NodeNG)
    inferred = node.inferred()
    assert len(inferred) == 1
    assert inferred[0] is Uninferable


def test_one_return() -> None:
    """Test function with a single return that always executes."""
    node = builder.extract_node(
        """
    def f():
        return 1

    f()  #@
    """
    )
    assert isinstance(node, nodes.NodeNG)
    inferred = node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == 1


def test_one_return_possible() -> None:
    """Test function with a single return that only sometimes executes.

    Note: currently, inference doesn't handle this type of control flow
    """
    node = builder.extract_node(
        """
    def f(x):
        if x:
            return 1

    f(1)  #@
    """
    )
    assert isinstance(node, nodes.NodeNG)
    inferred = node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == 1


def test_multiple_returns() -> None:
    """Test function with multiple returns."""
    node = builder.extract_node(
        """
    def f(x):
        if x > 10:
            return 1
        elif x > 20:
            return 2
        else:
            return 3

    f(100)  #@
    """
    )
    assert isinstance(node, nodes.NodeNG)
    inferred = node.inferred()
    assert len(inferred) == 3
    assert all(isinstance(node, nodes.Const) for node in inferred)
    assert {node.value for node in inferred} == {1, 2, 3}


def test_argument() -> None:
    """Test function whose return value uses its arguments."""
    node = builder.extract_node(
        """
    def f(x, y):
        return x + y

    f(1, 2)  #@
    """
    )
    assert isinstance(node, nodes.NodeNG)
    inferred = node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == 3


def test_inner_call() -> None:
    """Test function where return value is the result of a separate function call."""
    node = builder.extract_node(
        """
    def f():
        return g()

    def g():
        return 1

    f()  #@
    """
    )
    assert isinstance(node, nodes.NodeNG)
    inferred = node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == 1


def test_inner_call_with_const_argument() -> None:
    """Test function where return value is the result of a separate function call,
    with a constant value passed to the inner function.
    """
    node = builder.extract_node(
        """
    def f():
        return g(1)

    def g(y):
        return y + 2

    f()  #@
    """
    )
    assert isinstance(node, nodes.NodeNG)
    inferred = node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == 3


def test_inner_call_with_dynamic_argument() -> None:
    """Test function where return value is the result of a separate function call,
    with a dynamic value passed to the inner function.

    Currently, this is Uninferable.
    """
    node = builder.extract_node(
        """
    def f(x):
        return g(x)

    def g(y):
        return y + 2

    f(1)  #@
    """
    )
    assert isinstance(node, nodes.NodeNG)
    inferred = node.inferred()
    assert len(inferred) == 1
    assert inferred[0] is Uninferable


def test_method_const_instance_attr() -> None:
    """Test method where the return value is based on an instance attribute with a
    constant value.
    """
    node = builder.extract_node(
        """
    class A:
        def __init__(self):
            self.x = 1

        def get_x(self):
            return self.x

    A().get_x()  #@
    """
    )
    assert isinstance(node, nodes.NodeNG)
    inferred = node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == 1


def test_method_const_instance_attr_multiple() -> None:
    """Test method where the return value is based on an instance attribute with
    multiple possible constant values, across different methods.
    """
    node = builder.extract_node(
        """
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
    """
    )
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
    node = builder.extract_node(
        """
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
    """
    )
    assert isinstance(node, nodes.NodeNG)
    inferred = node.inferred()
    assert len(inferred) == 4
    assert all(isinstance(node, nodes.Const) for node in inferred)
    assert {node.value for node in inferred} == {1, 2, 3, 4}


def test_method_dynamic_instance_attr_1() -> None:
    """Test method where the return value is based on an instance attribute with
    a dynamically-set value in a different method.

    In this case, the return value is Uninferable.
    """
    node = builder.extract_node(
        """
    class A:
        def __init__(self, x):
            self.x = x

        def get_x(self):
            return self.x

    A(1).get_x()  #@
    """
    )
    assert isinstance(node, nodes.NodeNG)
    inferred = node.inferred()
    assert len(inferred) == 1
    assert inferred[0] is Uninferable


def test_method_dynamic_instance_attr_2() -> None:
    """Test method where the return value is based on an instance attribute with
    a dynamically-set value in the same method.
    """
    node = builder.extract_node(
        """
    class A:
        # Note: no initializer, so the only assignment happens in get_x

        def get_x(self, x):
            self.x = x
            return self.x

    A().get_x(1)  #@
    """
    )
    assert isinstance(node, nodes.NodeNG)
    inferred = node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == 1


def test_method_dynamic_instance_attr_3() -> None:
    """Test method where the return value is based on an instance attribute with
    a dynamically-set value in a different method.

    This is currently Uninferable.
    """
    node = builder.extract_node(
        """
    class A:
        def get_x(self, x):  # x is unused
            return self.x

        def set_x(self, x):
            self.x = x

    A().get_x(10)  #@
    """
    )
    assert isinstance(node, nodes.NodeNG)
    inferred = node.inferred()
    assert len(inferred) == 1
    assert inferred[0] is Uninferable  # not 10!


def test_method_dynamic_instance_attr_4() -> None:
    """Test method where the return value is based on an instance attribute with
    a dynamically-set value in a different method, and is passed a constant value.

    This is currently Uninferable.
    """
    node = builder.extract_node(
        """
    class A:
        # Note: no initializer, so the only assignment happens in get_x

        def get_x(self):
            self.set_x(10)
            return self.x

        def set_x(self, x):
            self.x = x

    A().get_x()  #@
    """
    )
    assert isinstance(node, nodes.NodeNG)
    inferred = node.inferred()
    assert len(inferred) == 1
    assert inferred[0] is Uninferable


def test_method_dynamic_instance_attr_5() -> None:
    """Test method where the return value is based on an instance attribute with
    a dynamically-set value in a different method, and is passed a constant value.

    But, where the outer and inner functions have the same signature.

    Inspired by https://github.com/pylint-dev/pylint/issues/400

    This is currently Uninferable.
    """
    node = builder.extract_node(
        """
    class A:
        # Note: no initializer, so the only assignment happens in get_x

        def get_x(self, x):
            self.set_x(10)
            return self.x

        def set_x(self, x):
            self.x = x

    A().get_x(1)  #@
    """
    )
    assert isinstance(node, nodes.NodeNG)
    inferred = node.inferred()
    assert len(inferred) == 1
    assert inferred[0] is Uninferable


def test_method_dynamic_instance_attr_6() -> None:
    """Test method where the return value is based on an instance attribute with
    a dynamically-set value in a different method, and is passed a dynamic value.

    This is currently Uninferable.
    """
    node = builder.extract_node(
        """
    class A:
        # Note: no initializer, so the only assignment happens in get_x

        def get_x(self, x):
            self.set_x(x + 1)
            return self.x

        def set_x(self, x):
            self.x = x

    A().get_x(1)  #@
    """
    )
    assert isinstance(node, nodes.NodeNG)
    inferred = node.inferred()
    assert len(inferred) == 1
    assert inferred[0] is Uninferable


def test_dunder_getitem() -> None:
    """Test for the special method __getitem__ (used by Instance.getitem).

    This is currently Uninferable, until we can infer instance attribute values through
    constructor calls.
    """
    node = builder.extract_node(
        """
    class A:
        def __init__(self, x):
            self.x = x

        def __getitem__(self, i):
            return self.x + i

    A(1)[2]  #@
    """
    )
    assert isinstance(node, nodes.NodeNG)
    inferred = node.inferred()
    assert len(inferred) == 1
    assert inferred[0] is Uninferable


def test_instance_method() -> None:
    """Tests for instance method, both bound and unbound."""
    nodes_ = builder.extract_node(
        """
    class A:
        def method(self, x):
            return x

    A().method(42)  #@

    # In this case, the 1 argument is bound to self, which is ignored in the method
    A.method(1, 42)  #@
    """
    )

    for node in nodes_:
        assert isinstance(node, nodes.NodeNG)
        inferred = node.inferred()
        assert len(inferred) == 1
        assert isinstance(inferred[0], nodes.Const)
        assert inferred[0].value == 42


def test_class_method() -> None:
    """Tests for class method calls, both instance and with the class."""
    nodes_ = builder.extract_node(
        """
    class A:
        @classmethod
        def method(cls, x):
            return x

    A.method(42)  #@
    A().method(42)  #@

    """
    )

    for node in nodes_:
        assert isinstance(node, nodes.NodeNG)
        inferred = node.inferred()
        assert len(inferred) == 1
        assert isinstance(inferred[0], nodes.Const), node
        assert inferred[0].value == 42


def test_static_method() -> None:
    """Tests for static method calls, both instance and with the class."""
    nodes_ = builder.extract_node(
        """
    class A:
        @staticmethod
        def method(x):
            return x

    A.method(42)  #@
    A().method(42)  #@
    """
    )

    for node in nodes_:
        assert isinstance(node, nodes.NodeNG)
        inferred = node.inferred()
        assert len(inferred) == 1
        assert isinstance(inferred[0], nodes.Const), node
        assert inferred[0].value == 42


def test_instance_method_inherited() -> None:
    """Tests for instance methods that are inherited from a superclass.

    Based on https://github.com/pylint-dev/astroid/issues/1008.
    """
    nodes_ = builder.extract_node(
        """
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
    """
    )
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
    nodes_ = builder.extract_node(
        """
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
    """
    )
    expected_names = ["A", "A", "B", "B"]
    for node, expected in zip(nodes_, expected_names):
        assert isinstance(node, nodes.NodeNG)
        inferred = node.inferred()
        assert len(inferred) == 1
        assert isinstance(inferred[0], nodes.ClassDef)
        assert inferred[0].name == expected


def test_chained_attribute_inherited() -> None:
    """Tests for class methods that are inherited from a superclass.

    Based on https://github.com/pylint-dev/pylint/issues/4220.
    """
    node = builder.extract_node(
        """
    class A:
        def f(self):
            return 42


    class B(A):
        def __init__(self):
            self.a = A()
            result = self.a.f()

        def f(self):
            pass


    B().a.f()  #@
    """
    )
    assert isinstance(node, nodes.NodeNG)
    inferred = node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == 42
