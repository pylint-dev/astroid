# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import unittest

from astroid import bases, builder, nodes, objects, util
from astroid.exceptions import AttributeInferenceError, InferenceError, SuperError
from astroid.objects import Super


class ObjectsTest(unittest.TestCase):
    def test_frozenset(self) -> None:
        node = builder.extract_node(
            """
        frozenset({1: 2, 2: 3}) #@
        """
        )
        inferred = next(node.infer())
        self.assertIsInstance(inferred, objects.FrozenSet)

        self.assertEqual(inferred.pytype(), "builtins.frozenset")

        itered = inferred.itered()
        self.assertEqual(len(itered), 2)
        self.assertIsInstance(itered[0], nodes.Const)
        self.assertEqual([const.value for const in itered], [1, 2])

        proxied = inferred._proxied
        self.assertEqual(inferred.qname(), "builtins.frozenset")
        self.assertIsInstance(proxied, nodes.ClassDef)

    def test_lookup_regression_slots(self) -> None:
        """Regression test for attr__new__ of ObjectModel.

        ObjectModel._instance is not always an bases.Instance, so we can't
        rely on the ._proxied attribute of an Instance.
        """

        node = builder.extract_node(
            """
        class ClassHavingUnknownAncestors(Unknown):
            __slots__ = ["yo"]

            def test(self):
                self.not_yo = 42
        """
        )
        assert node.getattr("__new__")


class SuperTests(unittest.TestCase):
    def test_inferring_super_outside_methods(self) -> None:
        ast_nodes = builder.extract_node(
            """
        class Module(object):
            pass
        class StaticMethod(object):
            @staticmethod
            def static():
                # valid, but we don't bother with it.
                return super(StaticMethod, StaticMethod) #@
        # super outside methods aren't inferred
        super(Module, Module) #@
        # no argument super is not recognised outside methods as well.
        super() #@
        """
        )
        assert isinstance(ast_nodes, list)
        in_static = next(ast_nodes[0].value.infer())
        self.assertIsInstance(in_static, bases.Instance)
        self.assertEqual(in_static.qname(), "builtins.super")

        module_level = next(ast_nodes[1].infer())
        self.assertIsInstance(module_level, bases.Instance)
        self.assertEqual(in_static.qname(), "builtins.super")

        no_arguments = next(ast_nodes[2].infer())
        self.assertIsInstance(no_arguments, bases.Instance)
        self.assertEqual(no_arguments.qname(), "builtins.super")

    def test_inferring_unbound_super_doesnt_work(self) -> None:
        node = builder.extract_node(
            """
        class Test(object):
            def __init__(self):
                super(Test) #@
        """
        )
        unbounded = next(node.infer())
        self.assertIsInstance(unbounded, bases.Instance)
        self.assertEqual(unbounded.qname(), "builtins.super")

    def test_use_default_inference_on_not_inferring_args(self) -> None:
        ast_nodes = builder.extract_node(
            """
        class Test(object):
            def __init__(self):
                super(Lala, self) #@
                super(Test, lala) #@
        """
        )
        assert isinstance(ast_nodes, list)
        first = next(ast_nodes[0].infer())
        self.assertIsInstance(first, bases.Instance)
        self.assertEqual(first.qname(), "builtins.super")

        second = next(ast_nodes[1].infer())
        self.assertIsInstance(second, bases.Instance)
        self.assertEqual(second.qname(), "builtins.super")

    def test_no_arguments_super(self) -> None:
        ast_nodes = builder.extract_node(
            """
        class First(object): pass
        class Second(First):
            def test(self):
                super() #@
            @classmethod
            def test_classmethod(cls):
                super() #@
        """
        )
        assert isinstance(ast_nodes, list)
        first = next(ast_nodes[0].infer())
        self.assertIsInstance(first, objects.Super)
        self.assertIsInstance(first.type, bases.Instance)
        self.assertEqual(first.type.name, "Second")
        self.assertIsInstance(first.mro_pointer, nodes.ClassDef)
        self.assertEqual(first.mro_pointer.name, "Second")

        second = next(ast_nodes[1].infer())
        self.assertIsInstance(second, objects.Super)
        self.assertIsInstance(second.type, nodes.ClassDef)
        self.assertEqual(second.type.name, "Second")
        self.assertIsInstance(second.mro_pointer, nodes.ClassDef)
        self.assertEqual(second.mro_pointer.name, "Second")

    def test_super_simple_cases(self) -> None:
        ast_nodes = builder.extract_node(
            """
        class First(object): pass
        class Second(First): pass
        class Third(First):
            def test(self):
                super(Third, self) #@
                super(Second, self) #@

                # mro position and the type
                super(Third, Third) #@
                super(Third, Second) #@
                super(Fourth, Fourth) #@

        class Fourth(Third):
            pass
        """
        )

        # .type is the object which provides the mro.
        # .mro_pointer is the position in the mro from where
        # the lookup should be done.

        # super(Third, self)
        assert isinstance(ast_nodes, list)
        first = next(ast_nodes[0].infer())
        self.assertIsInstance(first, objects.Super)
        self.assertIsInstance(first.type, bases.Instance)
        self.assertEqual(first.type.name, "Third")
        self.assertIsInstance(first.mro_pointer, nodes.ClassDef)
        self.assertEqual(first.mro_pointer.name, "Third")

        # super(Second, self)
        second = next(ast_nodes[1].infer())
        self.assertIsInstance(second, objects.Super)
        self.assertIsInstance(second.type, bases.Instance)
        self.assertEqual(second.type.name, "Third")
        self.assertIsInstance(first.mro_pointer, nodes.ClassDef)
        self.assertEqual(second.mro_pointer.name, "Second")

        # super(Third, Third)
        third = next(ast_nodes[2].infer())
        self.assertIsInstance(third, objects.Super)
        self.assertIsInstance(third.type, nodes.ClassDef)
        self.assertEqual(third.type.name, "Third")
        self.assertIsInstance(third.mro_pointer, nodes.ClassDef)
        self.assertEqual(third.mro_pointer.name, "Third")

        # super(Third, second)
        fourth = next(ast_nodes[3].infer())
        self.assertIsInstance(fourth, objects.Super)
        self.assertIsInstance(fourth.type, nodes.ClassDef)
        self.assertEqual(fourth.type.name, "Second")
        self.assertIsInstance(fourth.mro_pointer, nodes.ClassDef)
        self.assertEqual(fourth.mro_pointer.name, "Third")

        # Super(Fourth, Fourth)
        fifth = next(ast_nodes[4].infer())
        self.assertIsInstance(fifth, objects.Super)
        self.assertIsInstance(fifth.type, nodes.ClassDef)
        self.assertEqual(fifth.type.name, "Fourth")
        self.assertIsInstance(fifth.mro_pointer, nodes.ClassDef)
        self.assertEqual(fifth.mro_pointer.name, "Fourth")

    def test_super_infer(self) -> None:
        node = builder.extract_node(
            """
        class Super(object):
            def __init__(self):
                super(Super, self) #@
        """
        )
        inferred = next(node.infer())
        self.assertIsInstance(inferred, objects.Super)
        reinferred = next(inferred.infer())
        self.assertIsInstance(reinferred, objects.Super)
        self.assertIs(inferred, reinferred)

    def test_inferring_invalid_supers(self) -> None:
        ast_nodes = builder.extract_node(
            """
        class Super(object):
            def __init__(self):
                # MRO pointer is not a type
                super(1, self) #@
                # MRO type is not a subtype
                super(Super, 1) #@
                # self is not a subtype of Bupper
                super(Bupper, self) #@
        class Bupper(Super):
            pass
        """
        )
        assert isinstance(ast_nodes, list)
        first = next(ast_nodes[0].infer())
        self.assertIsInstance(first, objects.Super)
        with self.assertRaises(SuperError) as cm:
            first.super_mro()
        self.assertIsInstance(cm.exception.super_.mro_pointer, nodes.Const)
        self.assertEqual(cm.exception.super_.mro_pointer.value, 1)
        for node, invalid_type in zip(ast_nodes[1:], (nodes.Const, bases.Instance)):
            inferred = next(node.infer())
            self.assertIsInstance(inferred, objects.Super, node)
            with self.assertRaises(SuperError) as cm:
                inferred.super_mro()
            self.assertIsInstance(cm.exception.super_.type, invalid_type)

    def test_proxied(self) -> None:
        node = builder.extract_node(
            """
        class Super(object):
            def __init__(self):
                super(Super, self) #@
        """
        )
        inferred = next(node.infer())
        proxied = inferred._proxied
        self.assertEqual(proxied.qname(), "builtins.super")
        self.assertIsInstance(proxied, nodes.ClassDef)

    def test_super_bound_model(self) -> None:
        ast_nodes = builder.extract_node(
            """
        class First(object):
            def method(self):
                pass
            @classmethod
            def class_method(cls):
                pass
        class Super_Type_Type(First):
            def method(self):
                super(Super_Type_Type, Super_Type_Type).method #@
                super(Super_Type_Type, Super_Type_Type).class_method #@
            @classmethod
            def class_method(cls):
                super(Super_Type_Type, Super_Type_Type).method #@
                super(Super_Type_Type, Super_Type_Type).class_method #@

        class Super_Type_Object(First):
            def method(self):
                super(Super_Type_Object, self).method #@
                super(Super_Type_Object, self).class_method #@
        """
        )
        # Super(type, type) is the same for both functions and classmethods.
        assert isinstance(ast_nodes, list)
        first = next(ast_nodes[0].infer())
        self.assertIsInstance(first, nodes.FunctionDef)
        self.assertEqual(first.name, "method")

        second = next(ast_nodes[1].infer())
        self.assertIsInstance(second, bases.BoundMethod)
        self.assertEqual(second.bound.name, "First")
        self.assertEqual(second.type, "classmethod")

        third = next(ast_nodes[2].infer())
        self.assertIsInstance(third, nodes.FunctionDef)
        self.assertEqual(third.name, "method")

        fourth = next(ast_nodes[3].infer())
        self.assertIsInstance(fourth, bases.BoundMethod)
        self.assertEqual(fourth.bound.name, "First")
        self.assertEqual(fourth.type, "classmethod")

        # Super(type, obj) can lead to different attribute bindings
        # depending on the type of the place where super was called.
        fifth = next(ast_nodes[4].infer())
        self.assertIsInstance(fifth, bases.BoundMethod)
        self.assertEqual(fifth.bound.name, "First")
        self.assertEqual(fifth.type, "method")

        sixth = next(ast_nodes[5].infer())
        self.assertIsInstance(sixth, bases.BoundMethod)
        self.assertEqual(sixth.bound.name, "First")
        self.assertEqual(sixth.type, "classmethod")

    def test_super_getattr_single_inheritance(self) -> None:
        ast_nodes = builder.extract_node(
            """
        class First(object):
            def test(self): pass
        class Second(First):
            def test2(self): pass
        class Third(Second):
            test3 = 42
            def __init__(self):
                super(Third, self).test2 #@
                super(Third, self).test #@
                # test3 is local, no MRO lookup is done.
                super(Third, self).test3 #@
                super(Third, self) #@

                # Unbounds.
                super(Third, Third).test2 #@
                super(Third, Third).test #@

        """
        )
        assert isinstance(ast_nodes, list)
        first = next(ast_nodes[0].infer())
        self.assertIsInstance(first, bases.BoundMethod)
        self.assertEqual(first.bound.name, "Second")

        second = next(ast_nodes[1].infer())
        self.assertIsInstance(second, bases.BoundMethod)
        self.assertEqual(second.bound.name, "First")

        with self.assertRaises(InferenceError):
            next(ast_nodes[2].infer())
        fourth = next(ast_nodes[3].infer())
        with self.assertRaises(AttributeInferenceError):
            fourth.getattr("test3")
        with self.assertRaises(AttributeInferenceError):
            next(fourth.igetattr("test3"))

        first_unbound = next(ast_nodes[4].infer())
        self.assertIsInstance(first_unbound, nodes.FunctionDef)
        self.assertEqual(first_unbound.name, "test2")
        self.assertEqual(first_unbound.parent.name, "Second")

        second_unbound = next(ast_nodes[5].infer())
        self.assertIsInstance(second_unbound, nodes.FunctionDef)
        self.assertEqual(second_unbound.name, "test")
        self.assertEqual(second_unbound.parent.name, "First")

    def test_super_invalid_mro(self) -> None:
        node = builder.extract_node(
            """
        class A(object):
           test = 42
        class Super(A, A):
           def __init__(self):
               super(Super, self) #@
        """
        )
        inferred = next(node.infer())
        with self.assertRaises(AttributeInferenceError):
            next(inferred.getattr("test"))

    def test_super_complex_mro(self) -> None:
        ast_nodes = builder.extract_node(
            """
        class A(object):
            def spam(self): return "A"
            def foo(self): return "A"
            @staticmethod
            def static(self): pass
        class B(A):
            def boo(self): return "B"
            def spam(self): return "B"
        class C(A):
            def boo(self): return "C"
        class E(C, B):
            def __init__(self):
                super(E, self).boo #@
                super(C, self).boo #@
                super(E, self).spam #@
                super(E, self).foo #@
                super(E, self).static #@
        """
        )
        assert isinstance(ast_nodes, list)
        first = next(ast_nodes[0].infer())
        self.assertIsInstance(first, bases.BoundMethod)
        self.assertEqual(first.bound.name, "C")
        second = next(ast_nodes[1].infer())
        self.assertIsInstance(second, bases.BoundMethod)
        self.assertEqual(second.bound.name, "B")
        third = next(ast_nodes[2].infer())
        self.assertIsInstance(third, bases.BoundMethod)
        self.assertEqual(third.bound.name, "B")
        fourth = next(ast_nodes[3].infer())
        self.assertEqual(fourth.bound.name, "A")
        static = next(ast_nodes[4].infer())
        self.assertIsInstance(static, nodes.FunctionDef)
        self.assertEqual(static.parent.scope().name, "A")

    def test_super_data_model(self) -> None:
        ast_nodes = builder.extract_node(
            """
        class X(object): pass
        class A(X):
            def __init__(self):
                super(A, self) #@
                super(A, A) #@
                super(X, A) #@
        """
        )
        assert isinstance(ast_nodes, list)
        first = next(ast_nodes[0].infer())
        thisclass = first.getattr("__thisclass__")[0]
        self.assertIsInstance(thisclass, nodes.ClassDef)
        self.assertEqual(thisclass.name, "A")
        selfclass = first.getattr("__self_class__")[0]
        self.assertIsInstance(selfclass, nodes.ClassDef)
        self.assertEqual(selfclass.name, "A")
        self_ = first.getattr("__self__")[0]
        self.assertIsInstance(self_, bases.Instance)
        self.assertEqual(self_.name, "A")
        cls = first.getattr("__class__")[0]
        self.assertEqual(cls, first._proxied)

        second = next(ast_nodes[1].infer())
        thisclass = second.getattr("__thisclass__")[0]
        self.assertEqual(thisclass.name, "A")
        self_ = second.getattr("__self__")[0]
        self.assertIsInstance(self_, nodes.ClassDef)
        self.assertEqual(self_.name, "A")

        third = next(ast_nodes[2].infer())
        thisclass = third.getattr("__thisclass__")[0]
        self.assertEqual(thisclass.name, "X")
        selfclass = third.getattr("__self_class__")[0]
        self.assertEqual(selfclass.name, "A")

    def assertEqualMro(self, klass: Super, expected_mro: list[str]) -> None:
        self.assertEqual([member.name for member in klass.super_mro()], expected_mro)

    def test_super_mro(self) -> None:
        ast_nodes = builder.extract_node(
            """
        class A(object): pass
        class B(A): pass
        class C(A): pass
        class E(C, B):
            def __init__(self):
                super(E, self) #@
                super(C, self) #@
                super(B, self) #@

                super(B, 1) #@
                super(1, B) #@
        """
        )
        assert isinstance(ast_nodes, list)
        first = next(ast_nodes[0].infer())
        self.assertEqualMro(first, ["C", "B", "A", "object"])
        second = next(ast_nodes[1].infer())
        self.assertEqualMro(second, ["B", "A", "object"])
        third = next(ast_nodes[2].infer())
        self.assertEqualMro(third, ["A", "object"])

        fourth = next(ast_nodes[3].infer())
        with self.assertRaises(SuperError):
            fourth.super_mro()
        fifth = next(ast_nodes[4].infer())
        with self.assertRaises(SuperError):
            fifth.super_mro()

    def test_super_yes_objects(self) -> None:
        ast_nodes = builder.extract_node(
            """
        from collections import Missing
        class A(object):
            def __init__(self):
                super(Missing, self) #@
                super(A, Missing) #@
        """
        )
        assert isinstance(ast_nodes, list)
        first = next(ast_nodes[0].infer())
        self.assertIsInstance(first, bases.Instance)
        second = next(ast_nodes[1].infer())
        self.assertIsInstance(second, bases.Instance)

    def test_super_invalid_types(self) -> None:
        node = builder.extract_node(
            """
        import collections
        class A(object):
            def __init__(self):
                super(A, collections) #@
        """
        )
        inferred = next(node.infer())
        with self.assertRaises(SuperError):
            inferred.super_mro()
        with self.assertRaises(SuperError):
            inferred.super_mro()

    def test_super_properties(self) -> None:
        node = builder.extract_node(
            """
        class Foo(object):
            @property
            def dict(self):
                return 42

        class Bar(Foo):
            @property
            def dict(self):
                return super(Bar, self).dict

        Bar().dict
        """
        )
        inferred = next(node.infer())
        self.assertIsInstance(inferred, nodes.Const)
        self.assertEqual(inferred.value, 42)

    def test_super_qname(self) -> None:
        """Make sure a Super object generates a qname
        equivalent to super.__qname__.
        """
        # See issue 533
        code = """
        class C:
           def foo(self): return super()
        C().foo() #@
        """
        super_obj = next(builder.extract_node(code).infer())
        self.assertEqual(super_obj.qname(), "super")

    def test_super_new_call(self) -> None:
        """Test that __new__ returns an object or node and not a (Un)BoundMethod."""
        new_call_result: nodes.Name = builder.extract_node(
            """
        import enum
        class ChoicesMeta(enum.EnumMeta):
            def __new__(metacls, classname, bases, classdict, **kwds):
                cls = super().__new__(metacls, "str", (enum.Enum,), enum._EnumDict(), **kwargs)
                cls #@
        """
        )
        inferred = list(new_call_result.infer())
        assert all(
            isinstance(i, (nodes.NodeNG, type(util.Uninferable))) for i in inferred
        )

    def test_super_init_call(self) -> None:
        """Test that __init__ is still callable."""
        init_node: nodes.Attribute = builder.extract_node(
            """
        class SuperUsingClass:
            @staticmethod
            def test():
                super(object, 1).__new__ #@
                super(object, 1).__init__ #@
        class A:
            pass
        A().__new__ #@
        A().__init__ #@
        """
        )
        assert isinstance(next(init_node[0].infer()), bases.BoundMethod)
        assert isinstance(next(init_node[1].infer()), bases.BoundMethod)
        assert isinstance(next(init_node[2].infer()), bases.BoundMethod)
        assert isinstance(next(init_node[3].infer()), bases.BoundMethod)
