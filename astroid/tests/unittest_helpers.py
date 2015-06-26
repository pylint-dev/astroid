# copyright 2003-2015 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
# contact http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This file is part of astroid.
#
# astroid is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 2.1 of the License, or (at your
# option) any later version.
#
# astroid is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License
# for more details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with astroid. If not, see <http://www.gnu.org/licenses/>.

import unittest

import six
from six.moves import builtins

from astroid import bases
from astroid import helpers
from astroid import manager
from astroid import raw_building
from astroid import test_utils


class TestHelpers(unittest.TestCase):

    def setUp(self):
        builtins_name = builtins.__name__
        astroid_manager = manager.AstroidManager()
        self.builtins = astroid_manager.astroid_cache[builtins_name]
        self.manager = manager.AstroidManager()

    def _extract(self, obj_name):
        return self.builtins.getattr(obj_name)[0]

    def _build_custom_builtin(self, obj_name):
        proxy = raw_building.build_class(obj_name)
        proxy.parent = self.builtins
        return proxy

    def assert_classes_equal(self, cls, other):
        self.assertEqual(cls.name, other.name)
        self.assertEqual(cls.parent, other.parent)
        self.assertEqual(cls.qname(), other.qname())

    def test_object_type(self):
        pairs = [
            ('1', self._extract('int')),
            ('[]', self._extract('list')),
            ('{1, 2, 3}', self._extract('set')),
            ('{1:2, 4:3}', self._extract('dict')),
            ('type', self._extract('type')),
            ('object', self._extract('type')),
            ('object()', self._extract('object')),
            ('lambda: None', self._build_custom_builtin('function')),
            ('len', self._build_custom_builtin('builtin_function_or_method')),
            ('None', self._build_custom_builtin('NoneType')),
            ('import sys\nsys#@', self._build_custom_builtin('module')),
        ]
        for code, expected in pairs:
            node = test_utils.extract_node(code)
            objtype = helpers.object_type(node)
            self.assert_classes_equal(objtype, expected)

    def test_object_type_classes_and_functions(self):
        ast_nodes = test_utils.extract_node('''
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
        ''')
        from_self = helpers.object_type(ast_nodes[0])
        cls = next(ast_nodes[1].infer())
        self.assert_classes_equal(from_self, cls)

        cls_type = helpers.object_type(ast_nodes[1])
        self.assert_classes_equal(cls_type, self._extract('type'))

        instance_type = helpers.object_type(ast_nodes[2])
        cls = next(ast_nodes[2].infer())._proxied
        self.assert_classes_equal(instance_type, cls)

        expected_method_types = [
            (ast_nodes[3], 'instancemethod' if six.PY2 else 'function'),
            (ast_nodes[4], 'instancemethod' if six.PY2 else 'method'),
            (ast_nodes[5], 'instancemethod' if six.PY2 else 'method'),
            (ast_nodes[6], 'instancemethod' if six.PY2 else 'method'),
            (ast_nodes[7], 'function'),
            (ast_nodes[8], 'function'),
            (ast_nodes[9], 'generator'),
        ]
        for node, expected in expected_method_types:
            node_type = helpers.object_type(node)
            expected_type = self._build_custom_builtin(expected)
            self.assert_classes_equal(node_type, expected_type)

    @test_utils.require_version(minver='3.0')
    def test_object_type_metaclasses(self):
        module = test_utils.build_module('''
        import abc
        class Meta(metaclass=abc.ABCMeta):
            pass
        meta_instance = Meta()
        ''')
        meta_type = helpers.object_type(module['Meta'])
        self.assert_classes_equal(meta_type, module['Meta'].metaclass())

        meta_instance = next(module['meta_instance'].infer())
        instance_type = helpers.object_type(meta_instance)
        self.assert_classes_equal(instance_type, module['Meta'])

    @test_utils.require_version(minver='3.0')
    def test_object_type_most_derived(self):
        node = test_utils.extract_node('''
        class A(type):
            def __new__(*args, **kwargs):
                 return type.__new__(*args, **kwargs)
        class B(object): pass
        class C(object, metaclass=A): pass

        # The most derived metaclass of D is A rather than type.
        class D(B , C): #@
            pass
        ''')
        metaclass = node.metaclass()
        self.assertEqual(metaclass.name, 'A')
        obj_type = helpers.object_type(node)
        self.assertEqual(metaclass, obj_type)

    def test_inference_errors(self):
        node = test_utils.extract_node('''
        from unknown import Unknown
        u = Unknown #@
        ''')
        self.assertEqual(helpers.object_type(node), bases.YES)

    def test_object_type_too_many_types(self):
        node = test_utils.extract_node('''
        from unknown import Unknown
        def test(x):
            if x:
                return lambda: None
            else:
                return 1
        test(Unknown) #@
        ''')
        self.assertEqual(helpers.object_type(node), bases.YES)

    def test_is_subtype(self):
        ast_nodes = test_utils.extract_node('''
        class int_subclass(int):
            pass
        class A(object): pass #@
        class B(A): pass #@
        class C(A): pass #@
        int_subclass() #@
        ''')
        cls_a = ast_nodes[0]
        cls_b = ast_nodes[1]
        cls_c = ast_nodes[2]
        int_subclass = ast_nodes[3]
        int_subclass = helpers.object_type(next(int_subclass.infer()))
        base_int = self._extract('int')
        self.assertTrue(helpers.is_subtype(int_subclass, base_int))
        self.assertTrue(helpers.is_supertype(base_int, int_subclass))

        self.assertTrue(helpers.is_supertype(cls_a, cls_b))
        self.assertTrue(helpers.is_supertype(cls_a, cls_c))
        self.assertTrue(helpers.is_subtype(cls_b, cls_a))
        self.assertTrue(helpers.is_subtype(cls_c, cls_a))
        self.assertFalse(helpers.is_subtype(cls_a, cls_b))
        self.assertFalse(helpers.is_subtype(cls_a, cls_b))

    @test_utils.require_version(maxver='3.0')
    def test_is_subtype_supertype_old_style_classes(self):
        cls_a, cls_b = test_utils.extract_node('''
        class A: #@
            pass
        class B(A): #@
            pass
        ''')
        self.assertFalse(helpers.is_subtype(cls_a, cls_b))
        self.assertFalse(helpers.is_subtype(cls_b, cls_a))
        self.assertFalse(helpers.is_supertype(cls_a, cls_b))
        self.assertFalse(helpers.is_supertype(cls_b, cls_a))

    def test_is_subtype_supertype_mro_error(self):
        cls_e, cls_f = test_utils.extract_node('''
        class A(object): pass
        class B(A): pass
        class C(A): pass
        class D(B, C): pass
        class E(C, B): pass #@
        class F(D, E): pass #@
        ''')
        self.assertFalse(helpers.is_subtype(cls_e, cls_f))
        self.assertEqual(helpers.is_subtype(cls_f, cls_e), bases.YES)
        self.assertEqual(helpers.is_supertype(cls_e, cls_f), bases.YES)
        self.assertFalse(helpers.is_supertype(cls_f, cls_e))

    def test_is_subtype_supertype_unknown_bases(self):
        cls_a, cls_b = test_utils.extract_node('''
        from unknown import Unknown
        class A(Unknown): pass #@
        class B(A): pass #@
        ''')
        self.assertTrue(helpers.is_subtype(cls_b, cls_a))
        self.assertTrue(helpers.is_supertype(cls_a, cls_b))

    def test_is_subtype_supertype_unrelated_classes(self):
        cls_a, cls_b = test_utils.extract_node('''
        class A(object): pass #@
        class B(object): pass #@        
        ''')
        self.assertFalse(helpers.is_subtype(cls_a, cls_b))
        self.assertFalse(helpers.is_subtype(cls_b, cls_a))
        self.assertFalse(helpers.is_supertype(cls_a, cls_b))
        self.assertFalse(helpers.is_supertype(cls_b, cls_a))

    def test_is_subtype_supertype_classes_no_type_ancestor(self):
        cls_a = test_utils.extract_node('''
        class A(object): #@
            pass        
        ''')
        builtin_type = self._extract('type')
        self.assertFalse(helpers.is_supertype(builtin_type, cls_a))
        self.assertFalse(helpers.is_subtype(cls_a, builtin_type))

    def test_is_subtype_supertype_classes_metaclasses(self):
        cls_a = test_utils.extract_node('''
        class A(type): #@
            pass        
        ''')
        builtin_type = self._extract('type')
        self.assertTrue(helpers.is_supertype(builtin_type, cls_a))
        self.assertTrue(helpers.is_subtype(cls_a, builtin_type))


if __name__ == '__main__':
    unittest.main()
