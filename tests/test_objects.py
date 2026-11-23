# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import unittest

from astroid import bases, builder, nodes, objects, util
from astroid.exceptions import SuperError
from astroid.objects import Super


class SuperTests(unittest.TestCase):

    def test_super_infer(self) -> None:
        node = builder.extract_node("""
        class Super(object):
            def __init__(self):
                super(Super, self) #@
        """)
        inferred = next(node.infer())
        self.assertIsInstance(inferred, objects.Super)
        reinferred = next(inferred.infer())
        self.assertIsInstance(reinferred, objects.Super)
        self.assertIs(inferred, reinferred)

    def test_inferring_invalid_supers(self) -> None:
        ast_nodes = builder.extract_node("""
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
        """)
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

    def test_super_data_model(self) -> None:
        ast_nodes = builder.extract_node("""
        class X(object): pass
        class A(X):
            def __init__(self):
                super(A, self) #@
                super(A, A) #@
                super(X, A) #@
        """)
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
        new_call_result: nodes.Name = builder.extract_node("""
        import enum
        class ChoicesMeta(enum.EnumMeta):
            def __new__(metacls, classname, bases, classdict, **kwds):
                cls = super().__new__(metacls, "str", (enum.Enum,), enum._EnumDict(), **kwargs)
                cls #@
        """)
        inferred = list(new_call_result.infer())
        assert all(
            isinstance(i, (nodes.NodeNG, type(util.Uninferable))) for i in inferred
        )
