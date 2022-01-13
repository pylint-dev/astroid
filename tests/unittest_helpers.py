# Copyright (c) 2015-2016, 2018, 2020 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2015-2016 Ceridwen <ceridwenv@gmail.com>
# Copyright (c) 2019 Ashley Whetter <ashley@awhetter.co.uk>
# Copyright (c) 2020 David Gilman <davidgilman1@gmail.com>
# Copyright (c) 2021 Pierre Sassoulas <pierre.sassoulas@gmail.com>
# Copyright (c) 2021 Marc Mueller <30130371+cdce8p@users.noreply.github.com>
# Copyright (c) 2021 hippo91 <guillaume.peillex@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE


import builtins
import unittest

from astroid import builder, helpers, manager, nodes, raw_building, util
from astroid.exceptions import _NonDeducibleTypeHierarchy
from astroid.nodes.scoped_nodes import ClassDef


class TestHelpers(unittest.TestCase):
    def setUp(self) -> None:
        builtins_name = builtins.__name__
        astroid_manager = manager.AstroidManager()
        self.builtins = astroid_manager.astroid_cache[builtins_name]
        self.manager = manager.AstroidManager()

    def _extract(self, obj_name: str) -> ClassDef:
        return self.builtins.getattr(obj_name)[0]

    def _build_custom_builtin(self, obj_name: str) -> ClassDef:
        proxy = raw_building.build_class(obj_name)
        proxy.parent = self.builtins
        return proxy

    def assert_classes_equal(self, cls: ClassDef, other: ClassDef) -> None:
        self.assertEqual(cls.name, other.name)
        self.assertEqual(cls.parent, other.parent)
        self.assertEqual(cls.qname(), other.qname())

    def test_object_type(self) -> None:
        pairs = [
            ("1", self._extract("int")),
            ("[]", self._extract("list")),
            ("{1, 2, 3}", self._extract("set")),
            ("{1:2, 4:3}", self._extract("dict")),
            ("type", self._extract("type")),
            ("object", self._extract("type")),
            ("object()", self._extract("object")),
            ("lambda: None", self._build_custom_builtin("function")),
            ("len", self._build_custom_builtin("builtin_function_or_method")),
            ("None", self._build_custom_builtin("NoneType")),
            ("import sys\nsys#@", self._build_custom_builtin("module")),
        ]
        for code, expected in pairs:
            node = builder.extract_node(code)
            objtype = helpers.object_type(node)
            self.assert_classes_equal(objtype, expected)

    def test_object_type_classes_and_functions(self) -> None:
        ast_nodes = builder.extract_node(
            """
        def generator():
            yield

        class A(object):
            def test(self):
                self #@
            @classmethod
            def cls_method(cls): pass
            @staticmethod
            def static_method(): pass
        A #@
        A() #@
        A.test #@
        A().test #@
        A.cls_method #@
        A().cls_method #@
        A.static_method #@
        A().static_method #@
        generator() #@
        """
        )
        assert isinstance(ast_nodes, list)
        from_self = helpers.object_type(ast_nodes[0])
        cls = next(ast_nodes[1].infer())
        self.assert_classes_equal(from_self, cls)

        cls_type = helpers.object_type(ast_nodes[1])
        self.assert_classes_equal(cls_type, self._extract("type"))

        instance_type = helpers.object_type(ast_nodes[2])
        cls = next(ast_nodes[2].infer())._proxied
        self.assert_classes_equal(instance_type, cls)

        expected_method_types = [
            (ast_nodes[3], "function"),
            (ast_nodes[4], "method"),
            (ast_nodes[5], "method"),
            (ast_nodes[6], "method"),
            (ast_nodes[7], "function"),
            (ast_nodes[8], "function"),
            (ast_nodes[9], "generator"),
        ]
        for node, expected in expected_method_types:
            node_type = helpers.object_type(node)
            expected_type = self._build_custom_builtin(expected)
            self.assert_classes_equal(node_type, expected_type)

    def test_object_type_metaclasses(self) -> None:
        module = builder.parse(
            """
        import abc
        class Meta(metaclass=abc.ABCMeta):
            pass
        meta_instance = Meta()
        """
        )
        meta_type = helpers.object_type(module["Meta"])
        self.assert_classes_equal(meta_type, module["Meta"].metaclass())

        meta_instance = next(module["meta_instance"].infer())
        instance_type = helpers.object_type(meta_instance)
        self.assert_classes_equal(instance_type, module["Meta"])

    def test_object_type_most_derived(self) -> None:
        node = builder.extract_node(
            """
        class A(type):
            def __new__(*args, **kwargs):
                 return type.__new__(*args, **kwargs)
        class B(object): pass
        class C(object, metaclass=A): pass

        # The most derived metaclass of D is A rather than type.
        class D(B , C): #@
            pass
        """
        )
        assert isinstance(node, nodes.NodeNG)
        metaclass = node.metaclass()
        self.assertEqual(metaclass.name, "A")
        obj_type = helpers.object_type(node)
        self.assertEqual(metaclass, obj_type)

    def test_inference_errors(self) -> None:
        node = builder.extract_node(
            """
        from unknown import Unknown
        u = Unknown #@
        """
        )
        self.assertEqual(helpers.object_type(node), util.Uninferable)

    def test_object_type_too_many_types(self) -> None:
        node = builder.extract_node(
            """
        from unknown import Unknown
        def test(x):
            if x:
                return lambda: None
            else:
                return 1
        test(Unknown) #@
        """
        )
        self.assertEqual(helpers.object_type(node), util.Uninferable)

    def test_is_subtype(self) -> None:
        ast_nodes = builder.extract_node(
            """
        class int_subclass(int):
            pass
        class A(object): pass #@
        class B(A): pass #@
        class C(A): pass #@
        int_subclass() #@
        """
        )
        assert isinstance(ast_nodes, list)
        cls_a = ast_nodes[0]
        cls_b = ast_nodes[1]
        cls_c = ast_nodes[2]
        int_subclass = ast_nodes[3]
        int_subclass = helpers.object_type(next(int_subclass.infer()))
        base_int = self._extract("int")
        self.assertTrue(helpers.is_subtype(int_subclass, base_int))
        self.assertTrue(helpers.is_supertype(base_int, int_subclass))

        self.assertTrue(helpers.is_supertype(cls_a, cls_b))
        self.assertTrue(helpers.is_supertype(cls_a, cls_c))
        self.assertTrue(helpers.is_subtype(cls_b, cls_a))
        self.assertTrue(helpers.is_subtype(cls_c, cls_a))
        self.assertFalse(helpers.is_subtype(cls_a, cls_b))
        self.assertFalse(helpers.is_subtype(cls_a, cls_b))

    def test_is_subtype_supertype_mro_error(self) -> None:
        cls_e, cls_f = builder.extract_node(
            """
        class A(object): pass
        class B(A): pass
        class C(A): pass
        class D(B, C): pass
        class E(C, B): pass #@
        class F(D, E): pass #@
        """
        )
        self.assertFalse(helpers.is_subtype(cls_e, cls_f))

        self.assertFalse(helpers.is_subtype(cls_e, cls_f))
        with self.assertRaises(_NonDeducibleTypeHierarchy):
            helpers.is_subtype(cls_f, cls_e)
        self.assertFalse(helpers.is_supertype(cls_f, cls_e))

    def test_is_subtype_supertype_unknown_bases(self) -> None:
        cls_a, cls_b = builder.extract_node(
            """
        from unknown import Unknown
        class A(Unknown): pass #@
        class B(A): pass #@
        """
        )
        with self.assertRaises(_NonDeducibleTypeHierarchy):
            helpers.is_subtype(cls_a, cls_b)
        with self.assertRaises(_NonDeducibleTypeHierarchy):
            helpers.is_supertype(cls_a, cls_b)

    def test_is_subtype_supertype_unrelated_classes(self) -> None:
        cls_a, cls_b = builder.extract_node(
            """
        class A(object): pass #@
        class B(object): pass #@
        """
        )
        self.assertFalse(helpers.is_subtype(cls_a, cls_b))
        self.assertFalse(helpers.is_subtype(cls_b, cls_a))
        self.assertFalse(helpers.is_supertype(cls_a, cls_b))
        self.assertFalse(helpers.is_supertype(cls_b, cls_a))

    def test_is_subtype_supertype_classes_no_type_ancestor(self) -> None:
        cls_a = builder.extract_node(
            """
        class A(object): #@
            pass
        """
        )
        builtin_type = self._extract("type")
        self.assertFalse(helpers.is_supertype(builtin_type, cls_a))
        self.assertFalse(helpers.is_subtype(cls_a, builtin_type))

    def test_is_subtype_supertype_classes_metaclasses(self) -> None:
        cls_a = builder.extract_node(
            """
        class A(type): #@
            pass
        """
        )
        builtin_type = self._extract("type")
        self.assertTrue(helpers.is_supertype(builtin_type, cls_a))
        self.assertTrue(helpers.is_subtype(cls_a, builtin_type))

    def test_literal_eval(self):
        self.assertEqual(helpers.literal_eval('[1, 2, 3]'), [1, 2, 3])
        self.assertEqual(helpers.literal_eval('{"foo": 42}'), {"foo": 42})
        self.assertEqual(helpers.literal_eval('(True, False, None)'), (True, False, None))
        self.assertEqual(helpers.literal_eval('{1, 2, 3}'), {1, 2, 3})
        self.assertEqual(helpers.literal_eval('b"hi"'), b"hi")
        self.assertEqual(helpers.literal_eval('set()'), set())
        self.assertRaises(ValueError, helpers.literal_eval, 'foo()')
        self.assertEqual(helpers.literal_eval('6'), 6)
        self.assertEqual(helpers.literal_eval('+6'), 6)
        self.assertEqual(helpers.literal_eval('-6'), -6)
        self.assertEqual(helpers.literal_eval('3.25'), 3.25)
        self.assertEqual(helpers.literal_eval('+3.25'), 3.25)
        self.assertEqual(helpers.literal_eval('-3.25'), -3.25)
        self.assertEqual(repr(helpers.literal_eval('-0.0')), '-0.0')
        self.assertRaises(ValueError, helpers.literal_eval, '++6')
        self.assertRaises(ValueError, helpers.literal_eval, '+True')
        self.assertRaises(ValueError, helpers.literal_eval, '2+3')

    def test_literal_eval_complex(self):
        # Issue #4907
        self.assertEqual(helpers.literal_eval('6j'), 6j)
        self.assertEqual(helpers.literal_eval('-6j'), -6j)
        self.assertEqual(helpers.literal_eval('6.75j'), 6.75j)
        self.assertEqual(helpers.literal_eval('-6.75j'), -6.75j)
        self.assertEqual(helpers.literal_eval('3+6j'), 3+6j)
        self.assertEqual(helpers.literal_eval('-3+6j'), -3+6j)
        self.assertEqual(helpers.literal_eval('3-6j'), 3-6j)
        self.assertEqual(helpers.literal_eval('-3-6j'), -3-6j)
        self.assertEqual(helpers.literal_eval('3.25+6.75j'), 3.25+6.75j)
        self.assertEqual(helpers.literal_eval('-3.25+6.75j'), -3.25+6.75j)
        self.assertEqual(helpers.literal_eval('3.25-6.75j'), 3.25-6.75j)
        self.assertEqual(helpers.literal_eval('-3.25-6.75j'), -3.25-6.75j)
        self.assertEqual(helpers.literal_eval('(3+6j)'), 3+6j)
        self.assertRaises(ValueError, helpers.literal_eval, '-6j+3')
        self.assertRaises(ValueError, helpers.literal_eval, '-6j+3j')
        self.assertRaises(ValueError, helpers.literal_eval, '3+-6j')
        self.assertRaises(ValueError, helpers.literal_eval, '3+(0+6j)')
        self.assertRaises(ValueError, helpers.literal_eval, '-(3+6j)')
        self.assertRaises(ValueError, helpers.literal_eval, 'random()')

    def test_literal_eval_trailing_ws(self):
        self.assertEqual(helpers.literal_eval("    -1"), -1)
        self.assertEqual(helpers.literal_eval("\t\t-1"), -1)
        self.assertEqual(helpers.literal_eval(" \t -1"), -1)

    def test_literal_eval_malformed_lineno(self):
        msg = r'malformed node or string on line 3:'
        with self.assertRaisesRegex(ValueError, msg):
            helpers.literal_eval("{'a': 1,\n'b':2,\n'c':++3,\n'd':4}")

        op = nodes.UnaryOp("+")
        op.postinit(operand=nodes.Const(6))
        node = nodes.UnaryOp("+")
        node.postinit(operand=op)

        self.assertIsNone(getattr(node, 'lineno', None))
        msg = r'malformed node or string:'
        with self.assertRaisesRegex(ValueError, msg):
            helpers.literal_eval(node)

if __name__ == "__main__":
    unittest.main()
