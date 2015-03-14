# copyright 2003-2014 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
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
"""tests for specific behaviour of astroid scoped nodes (i.e. module, class and
function)
"""
import os
import sys
from functools import partial
import unittest
import warnings

from astroid import YES, builder, nodes, scoped_nodes, \
     InferenceError, NotFoundError, NoDefault, ResolveError
from astroid.bases import BUILTINS, Instance, BoundMethod, UnboundMethod
from astroid import __pkginfo__
from astroid import test_utils
from astroid.tests import resources


def _test_dict_interface(self, node, test_attr):
    self.assertIs(node[test_attr], node[test_attr])
    self.assertIn(test_attr, node)
    node.keys()
    node.values()
    node.items()
    iter(node)


class ModuleLoader(resources.SysPathSetup):
    def setUp(self):
        super(ModuleLoader, self).setUp()
        self.module = resources.build_file('data/module.py', 'data.module')
        self.module2 = resources.build_file('data/module2.py', 'data.module2')
        self.nonregr = resources.build_file('data/nonregr.py', 'data.nonregr')
        self.pack = resources.build_file('data/__init__.py', 'data')


class ModuleNodeTest(ModuleLoader, unittest.TestCase):

    def test_special_attributes(self):
        self.assertEqual(len(self.module.getattr('__name__')), 1)
        self.assertIsInstance(self.module.getattr('__name__')[0], nodes.Const)
        self.assertEqual(self.module.getattr('__name__')[0].value, 'data.module')
        self.assertEqual(len(self.module.getattr('__doc__')), 1)
        self.assertIsInstance(self.module.getattr('__doc__')[0], nodes.Const)
        self.assertEqual(self.module.getattr('__doc__')[0].value, 'test module for astroid\n')
        self.assertEqual(len(self.module.getattr('__file__')), 1)
        self.assertIsInstance(self.module.getattr('__file__')[0], nodes.Const)
        self.assertEqual(self.module.getattr('__file__')[0].value,
                         os.path.abspath(resources.find('data/module.py')))
        self.assertEqual(len(self.module.getattr('__dict__')), 1)
        self.assertIsInstance(self.module.getattr('__dict__')[0], nodes.Dict)
        self.assertRaises(NotFoundError, self.module.getattr, '__path__')
        self.assertEqual(len(self.pack.getattr('__path__')), 1)
        self.assertIsInstance(self.pack.getattr('__path__')[0], nodes.List)

    def test_dict_interface(self):
        _test_dict_interface(self, self.module, 'YO')

    def test_getattr(self):
        yo = self.module.getattr('YO')[0]
        self.assertIsInstance(yo, nodes.Class)
        self.assertEqual(yo.name, 'YO')
        red = next(self.module.igetattr('redirect'))
        self.assertIsInstance(red, nodes.Function)
        self.assertEqual(red.name, 'four_args')
        pb = next(self.module.igetattr('pb'))
        self.assertIsInstance(pb, nodes.Class)
        self.assertEqual(pb.name, 'ProgressBar')
        # resolve packageredirection
        mod = resources.build_file('data/appl/myConnection.py',
                                   'data.appl.myConnection')
        ssl = next(mod.igetattr('SSL1'))
        cnx = next(ssl.igetattr('Connection'))
        self.assertEqual(cnx.__class__, nodes.Class)
        self.assertEqual(cnx.name, 'Connection')
        self.assertEqual(cnx.root().name, 'data.SSL1.Connection1')
        self.assertEqual(len(self.nonregr.getattr('enumerate')), 2)
        # raise ResolveError
        self.assertRaises(InferenceError, self.nonregr.igetattr, 'YOAA')

    def test_wildard_import_names(self):
        m = resources.build_file('data/all.py', 'all')
        self.assertEqual(m.wildcard_import_names(), ['Aaa', '_bla', 'name'])
        m = resources.build_file('data/notall.py', 'notall')
        res = sorted(m.wildcard_import_names())
        self.assertEqual(res, ['Aaa', 'func', 'name', 'other'])

        m = test_utils.build_module('''
            from missing import tzop
            trop = "test"
            __all__ = (trop, "test1", tzop, 42)
        ''')
        res = sorted(m.wildcard_import_names())
        self.assertEqual(res, ["test", "test1"])

        m = test_utils.build_module('''
            test = tzop = 42
            __all__ = ('test', ) + ('tzop', )
        ''')
        res = sorted(m.wildcard_import_names())
        self.assertEqual(res, ['test', 'tzop'])

    def test_module_getattr(self):
        data = '''
            appli = application
            appli += 2
            del appli
        '''
        astroid = test_utils.build_module(data, __name__)
        # test del statement not returned by getattr
        self.assertEqual(len(astroid.getattr('appli')), 2,
                          astroid.getattr('appli'))

    def test_relative_to_absolute_name(self):
        # package
        mod = nodes.Module('very.multi.package', 'doc')
        mod.package = True
        modname = mod.relative_to_absolute_name('utils', 1)
        self.assertEqual(modname, 'very.multi.package.utils')
        modname = mod.relative_to_absolute_name('utils', 2)
        self.assertEqual(modname, 'very.multi.utils')
        modname = mod.relative_to_absolute_name('utils', 0)
        self.assertEqual(modname, 'very.multi.package.utils')
        modname = mod.relative_to_absolute_name('', 1)
        self.assertEqual(modname, 'very.multi.package')
        # non package
        mod = nodes.Module('very.multi.module', 'doc')
        mod.package = False
        modname = mod.relative_to_absolute_name('utils', 0)
        self.assertEqual(modname, 'very.multi.utils')
        modname = mod.relative_to_absolute_name('utils', 1)
        self.assertEqual(modname, 'very.multi.utils')
        modname = mod.relative_to_absolute_name('utils', 2)
        self.assertEqual(modname, 'very.utils')
        modname = mod.relative_to_absolute_name('', 1)
        self.assertEqual(modname, 'very.multi')

    def test_import_1(self):
        data = '''from . import subpackage'''
        sys.path.insert(0, resources.find('data'))
        astroid = test_utils.build_module(data, 'package', 'data/package/__init__.py')
        try:
            m = astroid.import_module('', level=1)
            self.assertEqual(m.name, 'package')
            infered = list(astroid.igetattr('subpackage'))
            self.assertEqual(len(infered), 1)
            self.assertEqual(infered[0].name, 'package.subpackage')
        finally:
            del sys.path[0]


    def test_import_2(self):
        data = '''from . import subpackage as pouet'''
        astroid = test_utils.build_module(data, 'package', 'data/package/__init__.py')
        sys.path.insert(0, resources.find('data'))
        try:
            m = astroid.import_module('', level=1)
            self.assertEqual(m.name, 'package')
            infered = list(astroid.igetattr('pouet'))
            self.assertEqual(len(infered), 1)
            self.assertEqual(infered[0].name, 'package.subpackage')
        finally:
            del sys.path[0]


    def test_file_stream_in_memory(self):
        data = '''irrelevant_variable is irrelevant'''
        astroid = test_utils.build_module(data, 'in_memory')
        with warnings.catch_warnings(record=True):
            self.assertEqual(astroid.file_stream.read().decode(), data)

    def test_file_stream_physical(self):
        path = resources.find('data/all.py')
        astroid = builder.AstroidBuilder().file_build(path, 'all')
        with open(path, 'rb') as file_io:
            with warnings.catch_warnings(record=True):
                self.assertEqual(astroid.file_stream.read(), file_io.read())

    def test_file_stream_api(self):
        path = resources.find('data/all.py')
        astroid = builder.AstroidBuilder().file_build(path, 'all')
        if __pkginfo__.numversion >= (1, 6):
            # file_stream is slated for removal in astroid 1.6.
            with self.assertRaises(AttributeError):
                astroid.file_stream
        else:
            # Until astroid 1.6, Module.file_stream will emit
            # PendingDeprecationWarning in 1.4, DeprecationWarning
            # in 1.5 and finally it will be removed in 1.6, leaving
            # only Module.stream as the recommended way to retrieve
            # its file stream.
            with warnings.catch_warnings(record=True) as cm:
                warnings.simplefilter("always")
                self.assertIsNot(astroid.file_stream, astroid.file_stream)
            self.assertGreater(len(cm), 1)
            self.assertEqual(cm[0].category, PendingDeprecationWarning)

    def test_stream_api(self):
        path = resources.find('data/all.py')
        astroid = builder.AstroidBuilder().file_build(path, 'all')
        stream = astroid.stream()
        self.assertTrue(hasattr(stream, 'close'))
        with stream:
            with open(path, 'rb') as file_io:
                self.assertEqual(stream.read(), file_io.read())


class FunctionNodeTest(ModuleLoader, unittest.TestCase):

    def test_special_attributes(self):
        func = self.module2['make_class']
        self.assertEqual(len(func.getattr('__name__')), 1)
        self.assertIsInstance(func.getattr('__name__')[0], nodes.Const)
        self.assertEqual(func.getattr('__name__')[0].value, 'make_class')
        self.assertEqual(len(func.getattr('__doc__')), 1)
        self.assertIsInstance(func.getattr('__doc__')[0], nodes.Const)
        self.assertEqual(func.getattr('__doc__')[0].value, 'check base is correctly resolved to Concrete0')
        self.assertEqual(len(self.module.getattr('__dict__')), 1)
        self.assertIsInstance(self.module.getattr('__dict__')[0], nodes.Dict)

    def test_dict_interface(self):
        _test_dict_interface(self, self.module['global_access'], 'local')

    def test_default_value(self):
        func = self.module2['make_class']
        self.assertIsInstance(func.args.default_value('base'), nodes.Getattr)
        self.assertRaises(NoDefault, func.args.default_value, 'args')
        self.assertRaises(NoDefault, func.args.default_value, 'kwargs')
        self.assertRaises(NoDefault, func.args.default_value, 'any')
        #self.assertIsInstance(func.mularg_class('args'), nodes.Tuple)
        #self.assertIsInstance(func.mularg_class('kwargs'), nodes.Dict)
        #self.assertIsNone(func.mularg_class('base'))

    def test_navigation(self):
        function = self.module['global_access']
        self.assertEqual(function.statement(), function)
        l_sibling = function.previous_sibling()
        # check taking parent if child is not a stmt
        self.assertIsInstance(l_sibling, nodes.Assign)
        child = function.args.args[0]
        self.assertIs(l_sibling, child.previous_sibling())
        r_sibling = function.next_sibling()
        self.assertIsInstance(r_sibling, nodes.Class)
        self.assertEqual(r_sibling.name, 'YO')
        self.assertIs(r_sibling, child.next_sibling())
        last = r_sibling.next_sibling().next_sibling().next_sibling()
        self.assertIsInstance(last, nodes.Assign)
        self.assertIsNone(last.next_sibling())
        first = l_sibling.previous_sibling().previous_sibling().previous_sibling().previous_sibling().previous_sibling()
        self.assertIsNone(first.previous_sibling())

    def test_nested_args(self):
        if sys.version_info >= (3, 0):
            self.skipTest("nested args has been removed in py3.x")
        code = '''
            def nested_args(a, (b, c, d)):
                "nested arguments test"
        '''
        tree = test_utils.build_module(code)
        func = tree['nested_args']
        self.assertEqual(sorted(func.locals), ['a', 'b', 'c', 'd'])
        self.assertEqual(func.args.format_args(), 'a, (b, c, d)')

    def test_four_args(self):
        func = self.module['four_args']
        #self.assertEqual(func.args.args, ['a', ('b', 'c', 'd')])
        local = sorted(func.keys())
        self.assertEqual(local, ['a', 'b', 'c', 'd'])
        self.assertEqual(func.type, 'function')

    def test_format_args(self):
        func = self.module2['make_class']
        self.assertEqual(func.args.format_args(),
                         'any, base=data.module.YO, *args, **kwargs')
        func = self.module['four_args']
        self.assertEqual(func.args.format_args(), 'a, b, c, d')

    def test_is_generator(self):
        self.assertTrue(self.module2['generator'].is_generator())
        self.assertFalse(self.module2['not_a_generator'].is_generator())
        self.assertFalse(self.module2['make_class'].is_generator())

    def test_is_abstract(self):
        method = self.module2['AbstractClass']['to_override']
        self.assertTrue(method.is_abstract(pass_is_abstract=False))
        self.assertEqual(method.qname(), 'data.module2.AbstractClass.to_override')
        self.assertEqual(method.pytype(), '%s.instancemethod' % BUILTINS)
        method = self.module2['AbstractClass']['return_something']
        self.assertFalse(method.is_abstract(pass_is_abstract=False))
        # non regression : test raise "string" doesn't cause an exception in is_abstract
        func = self.module2['raise_string']
        self.assertFalse(func.is_abstract(pass_is_abstract=False))

    def test_is_abstract_decorated(self):
        methods = test_utils.extract_node("""
            import abc

            class Klass(object):
                @abc.abstractproperty
                def prop(self):  #@
                   pass

                @abc.abstractmethod
                def method1(self):  #@
                   pass

                some_other_decorator = lambda x: x
                @some_other_decorator
                def method2(self):  #@
                   pass
         """)
        self.assertTrue(methods[0].is_abstract(pass_is_abstract=False))
        self.assertTrue(methods[1].is_abstract(pass_is_abstract=False))
        self.assertFalse(methods[2].is_abstract(pass_is_abstract=False))

##     def test_raises(self):
##         method = self.module2['AbstractClass']['to_override']
##         self.assertEqual([str(term) for term in method.raises()],
##                           ["CallFunc(Name('NotImplementedError'), [], None, None)"] )

##     def test_returns(self):
##         method = self.module2['AbstractClass']['return_something']
##         # use string comp since Node doesn't handle __cmp__
##         self.assertEqual([str(term) for term in method.returns()],
##                           ["Const('toto')", "Const(None)"])

    def test_lambda_pytype(self):
        data = '''
            def f():
                g = lambda: None
        '''
        astroid = test_utils.build_module(data)
        g = list(astroid['f'].ilookup('g'))[0]
        self.assertEqual(g.pytype(), '%s.function' % BUILTINS)

    def test_lambda_qname(self):
        astroid = test_utils.build_module('lmbd = lambda: None', __name__)
        self.assertEqual('%s.<lambda>' % __name__, astroid['lmbd'].parent.value.qname())

    def test_is_method(self):
        data = '''
            class A:
                def meth1(self):
                    return 1
                @classmethod
                def meth2(cls):
                    return 2
                @staticmethod
                def meth3():
                    return 3

            def function():
                return 0

            @staticmethod
            def sfunction():
                return -1
        '''
        astroid = test_utils.build_module(data)
        self.assertTrue(astroid['A']['meth1'].is_method())
        self.assertTrue(astroid['A']['meth2'].is_method())
        self.assertTrue(astroid['A']['meth3'].is_method())
        self.assertFalse(astroid['function'].is_method())
        self.assertFalse(astroid['sfunction'].is_method())

    def test_argnames(self):
        if sys.version_info < (3, 0):
            code = 'def f(a, (b, c), *args, **kwargs): pass'
        else:
            code = 'def f(a, b, c, *args, **kwargs): pass'
        astroid = test_utils.build_module(code, __name__)
        self.assertEqual(astroid['f'].argnames(), ['a', 'b', 'c', 'args', 'kwargs'])

    def test_return_nothing(self):
        """test infered value on a function with empty return"""
        data = '''
            def func():
                return

            a = func()
        '''
        astroid = test_utils.build_module(data)
        call = astroid.body[1].value
        func_vals = call.infered()
        self.assertEqual(len(func_vals), 1)
        self.assertIsInstance(func_vals[0], nodes.Const)
        self.assertIsNone(func_vals[0].value)

    def test_func_instance_attr(self):
        """test instance attributes for functions"""
        data = """
            def test():
                print(test.bar)

            test.bar = 1
            test()
        """
        astroid = test_utils.build_module(data, 'mod')
        func = astroid.body[2].value.func.infered()[0]
        self.assertIsInstance(func, nodes.Function)
        self.assertEqual(func.name, 'test')
        one = func.getattr('bar')[0].infered()[0]
        self.assertIsInstance(one, nodes.Const)
        self.assertEqual(one.value, 1)

    def test_type_builtin_descriptor_subclasses(self):
        astroid = test_utils.build_module("""
            class classonlymethod(classmethod):
                pass
            class staticonlymethod(staticmethod):
                pass

            class Node:
                @classonlymethod
                def clsmethod_subclass(cls):
                    pass
                @classmethod
                def clsmethod(cls):
                    pass
                @staticonlymethod
                def staticmethod_subclass(cls):
                    pass
                @staticmethod
                def stcmethod(cls):
                    pass
        """)
        node = astroid.locals['Node'][0]
        self.assertEqual(node.locals['clsmethod_subclass'][0].type,
                         'classmethod')
        self.assertEqual(node.locals['clsmethod'][0].type,
                         'classmethod')
        self.assertEqual(node.locals['staticmethod_subclass'][0].type,
                         'staticmethod')
        self.assertEqual(node.locals['stcmethod'][0].type,
                         'staticmethod')

    def test_decorator_builtin_descriptors(self):
        astroid = test_utils.build_module("""
            def static_decorator(platform=None, order=50):
                def wrapper(f):
                    f.cgm_module = True
                    f.cgm_module_order = order
                    f.cgm_module_platform = platform
                    return staticmethod(f)
                return wrapper

            def long_classmethod_decorator(platform=None, order=50):
                def wrapper(f):
                    def wrapper2(f):
                        def wrapper3(f):
                            f.cgm_module = True
                            f.cgm_module_order = order
                            f.cgm_module_platform = platform
                            return classmethod(f)
                        return wrapper3(f)
                    return wrapper2(f)
                return wrapper

            def classmethod_decorator(platform=None):
                def wrapper(f):
                    f.platform = platform
                    return classmethod(f)
                return wrapper

            def classmethod_wrapper(fn):
                def wrapper(cls, *args, **kwargs):
                    result = fn(cls, *args, **kwargs)
                    return result

                return classmethod(wrapper)

            def staticmethod_wrapper(fn):
                def wrapper(*args, **kwargs):
                    return fn(*args, **kwargs)
                return staticmethod(wrapper)

            class SomeClass(object):
                @static_decorator()
                def static(node, cfg):
                    pass
                @classmethod_decorator()
                def classmethod(cls):
                    pass
                @static_decorator
                def not_so_static(node):
                    pass
                @classmethod_decorator
                def not_so_classmethod(node):
                    pass
                @classmethod_wrapper
                def classmethod_wrapped(cls):
                    pass
                @staticmethod_wrapper
                def staticmethod_wrapped():
                    pass
                @long_classmethod_decorator()
                def long_classmethod(cls): 
                    pass
        """)
        node = astroid.locals['SomeClass'][0]
        self.assertEqual(node.locals['static'][0].type,
                         'staticmethod')
        self.assertEqual(node.locals['classmethod'][0].type,
                         'classmethod')
        self.assertEqual(node.locals['not_so_static'][0].type,
                         'method')
        self.assertEqual(node.locals['not_so_classmethod'][0].type,
                         'method')
        self.assertEqual(node.locals['classmethod_wrapped'][0].type,
                         'classmethod')
        self.assertEqual(node.locals['staticmethod_wrapped'][0].type,
                         'staticmethod')
        self.assertEqual(node.locals['long_classmethod'][0].type,
                         'classmethod')


class ClassNodeTest(ModuleLoader, unittest.TestCase):

    def test_dict_interface(self):
        _test_dict_interface(self, self.module['YOUPI'], 'method')

    def test_cls_special_attributes_1(self):
        cls = self.module['YO']
        self.assertEqual(len(cls.getattr('__bases__')), 1)
        self.assertEqual(len(cls.getattr('__name__')), 1)
        self.assertIsInstance(cls.getattr('__name__')[0], nodes.Const)
        self.assertEqual(cls.getattr('__name__')[0].value, 'YO')
        self.assertEqual(len(cls.getattr('__doc__')), 1)
        self.assertIsInstance(cls.getattr('__doc__')[0], nodes.Const)
        self.assertEqual(cls.getattr('__doc__')[0].value, 'hehe')
        self.assertEqual(len(cls.getattr('__module__')), 1)
        self.assertIsInstance(cls.getattr('__module__')[0], nodes.Const)
        self.assertEqual(cls.getattr('__module__')[0].value, 'data.module')
        self.assertEqual(len(cls.getattr('__dict__')), 1)
        if not cls.newstyle:
            self.assertRaises(NotFoundError, cls.getattr, '__mro__')
        for cls in (nodes.List._proxied, nodes.Const(1)._proxied):
            self.assertEqual(len(cls.getattr('__bases__')), 1)
            self.assertEqual(len(cls.getattr('__name__')), 1)
            self.assertEqual(len(cls.getattr('__doc__')), 1, (cls, cls.getattr('__doc__')))
            self.assertEqual(cls.getattr('__doc__')[0].value, cls.doc)
            self.assertEqual(len(cls.getattr('__module__')), 1)
            self.assertEqual(len(cls.getattr('__dict__')), 1)
            self.assertEqual(len(cls.getattr('__mro__')), 1)

    def test_cls_special_attributes_2(self):
        astroid = test_utils.build_module('''
            class A: pass
            class B: pass

            A.__bases__ += (B,)
        ''', __name__)
        self.assertEqual(len(astroid['A'].getattr('__bases__')), 2)
        self.assertIsInstance(astroid['A'].getattr('__bases__')[0], nodes.Tuple)
        self.assertIsInstance(astroid['A'].getattr('__bases__')[1], nodes.AssAttr)

    def test_instance_special_attributes(self):
        for inst in (Instance(self.module['YO']), nodes.List(), nodes.Const(1)):
            self.assertRaises(NotFoundError, inst.getattr, '__mro__')
            self.assertRaises(NotFoundError, inst.getattr, '__bases__')
            self.assertRaises(NotFoundError, inst.getattr, '__name__')
            self.assertEqual(len(inst.getattr('__dict__')), 1)
            self.assertEqual(len(inst.getattr('__doc__')), 1)

    def test_navigation(self):
        klass = self.module['YO']
        self.assertEqual(klass.statement(), klass)
        l_sibling = klass.previous_sibling()
        self.assertTrue(isinstance(l_sibling, nodes.Function), l_sibling)
        self.assertEqual(l_sibling.name, 'global_access')
        r_sibling = klass.next_sibling()
        self.assertIsInstance(r_sibling, nodes.Class)
        self.assertEqual(r_sibling.name, 'YOUPI')

    def test_local_attr_ancestors(self):
        klass2 = self.module['YOUPI']
        it = klass2.local_attr_ancestors('__init__')
        anc_klass = next(it)
        self.assertIsInstance(anc_klass, nodes.Class)
        self.assertEqual(anc_klass.name, 'YO')
        if sys.version_info[0] == 2:
            self.assertRaises(StopIteration, partial(next, it))
        else:
            anc_klass = next(it)
            self.assertIsInstance(anc_klass, nodes.Class)
            self.assertEqual(anc_klass.name, 'object')
            self.assertRaises(StopIteration, partial(next, it))

        it = klass2.local_attr_ancestors('method')
        self.assertRaises(StopIteration, partial(next, it))

    def test_instance_attr_ancestors(self):
        klass2 = self.module['YOUPI']
        it = klass2.instance_attr_ancestors('yo')
        anc_klass = next(it)
        self.assertIsInstance(anc_klass, nodes.Class)
        self.assertEqual(anc_klass.name, 'YO')
        self.assertRaises(StopIteration, partial(next, it))
        klass2 = self.module['YOUPI']
        it = klass2.instance_attr_ancestors('member')
        self.assertRaises(StopIteration, partial(next, it))

    def test_methods(self):
        expected_methods = {'__init__', 'class_method', 'method', 'static_method'}
        klass2 = self.module['YOUPI']
        methods = {m.name for m in klass2.methods()}
        self.assertTrue(
            methods.issuperset(expected_methods))
        methods = {m.name for m in klass2.mymethods()}
        self.assertSetEqual(expected_methods, methods)
        klass2 = self.module2['Specialization']
        methods = {m.name for m in klass2.mymethods()}
        self.assertSetEqual(set([]), methods)
        method_locals = klass2.local_attr('method')
        self.assertEqual(len(method_locals), 1)
        self.assertEqual(method_locals[0].name, 'method')
        self.assertRaises(NotFoundError, klass2.local_attr, 'nonexistant')
        methods = {m.name for m in klass2.methods()}
        self.assertTrue(methods.issuperset(expected_methods))

    #def test_rhs(self):
    #    my_dict = self.module['MY_DICT']
    #    self.assertIsInstance(my_dict.rhs(), nodes.Dict)
    #    a = self.module['YO']['a']
    #    value = a.rhs()
    #    self.assertIsInstance(value, nodes.Const)
    #    self.assertEqual(value.value, 1)

    @unittest.skipIf(sys.version_info[0] >= 3, "Python 2 class semantics required.")
    def test_ancestors(self):
        klass = self.module['YOUPI']
        self.assertEqual(['YO'], [a.name for a in klass.ancestors()])
        klass = self.module2['Specialization']
        self.assertEqual(['YOUPI', 'YO'], [a.name for a in klass.ancestors()])

    @unittest.skipIf(sys.version_info[0] < 3, "Python 3 class semantics required.")
    def test_ancestors_py3(self):
        klass = self.module['YOUPI']
        self.assertEqual(['YO', 'object'], [a.name for a in klass.ancestors()])
        klass = self.module2['Specialization']
        self.assertEqual(['YOUPI', 'YO', 'object'], [a.name for a in klass.ancestors()])

    def test_type(self):
        klass = self.module['YOUPI']
        self.assertEqual(klass.type, 'class')
        klass = self.module2['Metaclass']
        self.assertEqual(klass.type, 'metaclass')
        klass = self.module2['MyException']
        self.assertEqual(klass.type, 'exception')
        klass = self.module2['MyIFace']
        self.assertEqual(klass.type, 'interface')
        klass = self.module2['MyError']
        self.assertEqual(klass.type, 'exception')
        # the following class used to be detected as a metaclass
        # after the fix which used instance._proxied in .ancestors(),
        # when in fact it is a normal class
        klass = self.module2['NotMetaclass']
        self.assertEqual(klass.type, 'class')

    def test_interfaces(self):
        for klass, interfaces in (('Concrete0', ['MyIFace']),
                                  ('Concrete1', ['MyIFace', 'AnotherIFace']),
                                  ('Concrete2', ['MyIFace', 'AnotherIFace']),
                                  ('Concrete23', ['MyIFace', 'AnotherIFace'])):
            klass = self.module2[klass]
            self.assertEqual([i.name for i in klass.interfaces()],
                              interfaces)

    def test_concat_interfaces(self):
        astroid = test_utils.build_module('''
            class IMachin: pass

            class Correct2:
                """docstring"""
                __implements__ = (IMachin,)

            class BadArgument:
                """docstring"""
                __implements__ = (IMachin,)

            class InterfaceCanNowBeFound:
                """docstring"""
                __implements__ = BadArgument.__implements__ + Correct2.__implements__
        ''')
        self.assertEqual([i.name for i in astroid['InterfaceCanNowBeFound'].interfaces()],
                          ['IMachin'])

    def test_inner_classes(self):
        eee = self.nonregr['Ccc']['Eee']
        self.assertEqual([n.name for n in eee.ancestors()], ['Ddd', 'Aaa', 'object'])


    def test_classmethod_attributes(self):
        data = '''
            class WebAppObject(object):
                def registered(cls, application):
                    cls.appli = application
                    cls.schema = application.schema
                    cls.config = application.config
                    return cls
                registered = classmethod(registered)
        '''
        astroid = test_utils.build_module(data, __name__)
        cls = astroid['WebAppObject']
        self.assertEqual(sorted(cls.locals.keys()),
                          ['appli', 'config', 'registered', 'schema'])


    def test_class_getattr(self):
        data = '''
            class WebAppObject(object):
                appli = application
                appli += 2
                del self.appli
        '''
        astroid = test_utils.build_module(data, __name__)
        cls = astroid['WebAppObject']
        # test del statement not returned by getattr
        self.assertEqual(len(cls.getattr('appli')), 2)


    def test_instance_getattr(self):
        data = '''
            class WebAppObject(object):
                def __init__(self, application):
                    self.appli = application
                    self.appli += 2
                    del self.appli
         '''
        astroid = test_utils.build_module(data)
        inst = Instance(astroid['WebAppObject'])
        # test del statement not returned by getattr
        self.assertEqual(len(inst.getattr('appli')), 2)


    def test_instance_getattr_with_class_attr(self):
        data = '''
            class Parent:
                aa = 1
                cc = 1

            class Klass(Parent):
                aa = 0
                bb = 0

                def incr(self, val):
                    self.cc = self.aa
                    if val > self.aa:
                        val = self.aa
                    if val < self.bb:
                        val = self.bb
                    self.aa += val
        '''
        astroid = test_utils.build_module(data)
        inst = Instance(astroid['Klass'])
        self.assertEqual(len(inst.getattr('aa')), 3, inst.getattr('aa'))
        self.assertEqual(len(inst.getattr('bb')), 1, inst.getattr('bb'))
        self.assertEqual(len(inst.getattr('cc')), 2, inst.getattr('cc'))


    def test_getattr_method_transform(self):
        data = '''
            class Clazz(object):

                def m1(self, value):
                    self.value = value
                m2 = m1

            def func(arg1, arg2):
                "function that will be used as a method"
                return arg1.value + arg2

            Clazz.m3 = func
            inst = Clazz()
            inst.m4 = func
        '''
        astroid = test_utils.build_module(data)
        cls = astroid['Clazz']
        # test del statement not returned by getattr
        for method in ('m1', 'm2', 'm3'):
            inferred = list(cls.igetattr(method))
            self.assertEqual(len(inferred), 1)
            self.assertIsInstance(inferred[0], UnboundMethod)
            inferred = list(Instance(cls).igetattr(method))
            self.assertEqual(len(inferred), 1)
            self.assertIsInstance(inferred[0], BoundMethod)
        inferred = list(Instance(cls).igetattr('m4'))
        self.assertEqual(len(inferred), 1)
        self.assertIsInstance(inferred[0], nodes.Function)

    def test_getattr_from_grandpa(self):
        data = '''
            class Future:
                attr = 1

            class Present(Future):
                pass

            class Past(Present):
                pass
        '''
        astroid = test_utils.build_module(data)
        past = astroid['Past']
        attr = past.getattr('attr')
        self.assertEqual(len(attr), 1)
        attr1 = attr[0]
        self.assertIsInstance(attr1, nodes.AssName)
        self.assertEqual(attr1.name, 'attr')

    def test_function_with_decorator_lineno(self):
        data = '''
            @f(a=2,
               b=3)
            def g1(x):
                print(x)

            @f(a=2,
               b=3)
            def g2():
                pass
        '''
        astroid = test_utils.build_module(data)
        self.assertEqual(astroid['g1'].fromlineno, 4)
        self.assertEqual(astroid['g1'].tolineno, 5)
        self.assertEqual(astroid['g2'].fromlineno, 9)
        self.assertEqual(astroid['g2'].tolineno, 10)

    @test_utils.require_version(maxver='3.0')
    def test_simple_metaclass(self):
        astroid = test_utils.build_module("""
            class Test(object):
                __metaclass__ = type
        """)
        klass = astroid['Test']
        metaclass = klass.metaclass()
        self.assertIsInstance(metaclass, scoped_nodes.Class)
        self.assertEqual(metaclass.name, 'type')

    def test_metaclass_error(self):
        astroid = test_utils.build_module("""
            class Test(object):
                __metaclass__ = typ
        """)
        klass = astroid['Test']
        self.assertFalse(klass.metaclass())

    @test_utils.require_version(maxver='3.0')
    def test_metaclass_imported(self):
        astroid = test_utils.build_module("""
            from abc import ABCMeta
            class Test(object):
                __metaclass__ = ABCMeta
        """)
        klass = astroid['Test']

        metaclass = klass.metaclass()
        self.assertIsInstance(metaclass, scoped_nodes.Class)
        self.assertEqual(metaclass.name, 'ABCMeta')

    def test_metaclass_yes_leak(self):
        astroid = test_utils.build_module("""
            # notice `ab` instead of `abc`
            from ab import ABCMeta

            class Meta(object):
                __metaclass__ = ABCMeta
        """)
        klass = astroid['Meta']
        self.assertIsNone(klass.metaclass())

    @test_utils.require_version(maxver='3.0')
    def test_newstyle_and_metaclass_good(self):
        astroid = test_utils.build_module("""
            from abc import ABCMeta
            class Test:
                __metaclass__ = ABCMeta
        """)
        klass = astroid['Test']
        self.assertTrue(klass.newstyle)
        self.assertEqual(klass.metaclass().name, 'ABCMeta')
        astroid = test_utils.build_module("""
            from abc import ABCMeta
            __metaclass__ = ABCMeta
            class Test:
                pass
        """)
        klass = astroid['Test']
        self.assertTrue(klass.newstyle)
        self.assertEqual(klass.metaclass().name, 'ABCMeta')

    @test_utils.require_version(maxver='3.0')
    def test_nested_metaclass(self):
        astroid = test_utils.build_module("""
            from abc import ABCMeta
            class A(object):
                __metaclass__ = ABCMeta
                class B: pass

            __metaclass__ = ABCMeta
            class C:
               __metaclass__ = type
               class D: pass
        """)
        a = astroid['A']
        b = a.locals['B'][0]
        c = astroid['C']
        d = c.locals['D'][0]
        self.assertEqual(a.metaclass().name, 'ABCMeta')
        self.assertFalse(b.newstyle)
        self.assertIsNone(b.metaclass())
        self.assertEqual(c.metaclass().name, 'type')
        self.assertEqual(d.metaclass().name, 'ABCMeta')

    @test_utils.require_version(maxver='3.0')
    def test_parent_metaclass(self):
        astroid = test_utils.build_module("""
            from abc import ABCMeta
            class Test:
                __metaclass__ = ABCMeta
            class SubTest(Test): pass
        """)
        klass = astroid['SubTest']
        self.assertTrue(klass.newstyle)
        metaclass = klass.metaclass()
        self.assertIsInstance(metaclass, scoped_nodes.Class)
        self.assertEqual(metaclass.name, 'ABCMeta')

    @test_utils.require_version(maxver='3.0')
    def test_metaclass_ancestors(self):
        astroid = test_utils.build_module("""
            from abc import ABCMeta

            class FirstMeta(object):
                __metaclass__ = ABCMeta

            class SecondMeta(object):
                __metaclass__ = type

            class Simple(object):
                pass

            class FirstImpl(FirstMeta): pass
            class SecondImpl(FirstImpl): pass
            class ThirdImpl(Simple, SecondMeta):
                pass
        """)
        classes = {
            'ABCMeta': ('FirstImpl', 'SecondImpl'),
            'type': ('ThirdImpl', )
        }
        for metaclass, names in classes.items():
            for name in names:
                impl = astroid[name]
                meta = impl.metaclass()
                self.assertIsInstance(meta, nodes.Class)
                self.assertEqual(meta.name, metaclass)

    def test_metaclass_type(self):
        klass = test_utils.extract_node("""
            def with_metaclass(meta, base=object):
                return meta("NewBase", (base, ), {})

            class ClassWithMeta(with_metaclass(type)): #@
                pass
        """)
        self.assertEqual(
            ['NewBase', 'object'],
            [base.name for base in klass.ancestors()])

    def test_metaclass_generator_hack(self):
        klass = test_utils.extract_node("""
            import six

            class WithMeta(six.with_metaclass(type, object)): #@
                pass
        """)
        self.assertEqual(
            ['object'],
            [base.name for base in klass.ancestors()])
        self.assertEqual(
            'type', klass.metaclass().name)

    def test_nonregr_infer_callresult(self):
        astroid = test_utils.build_module("""
            class Delegate(object):
                def __get__(self, obj, cls):
                    return getattr(obj._subject, self.attribute)

            class CompositeBuilder(object):
                __call__ = Delegate()

            builder = CompositeBuilder(result, composite)
            tgts = builder()
        """)
        instance = astroid['tgts']
        # used to raise "'_Yes' object is not iterable", see
        # https://bitbucket.org/logilab/astroid/issue/17
        self.assertEqual(list(instance.infer()), [YES])

    def test_slots(self):
        astroid = test_utils.build_module("""
            from collections import deque
            from textwrap import dedent

            class First(object):
                __slots__ = ("a", "b", 1)
            class Second(object):
                __slots__ = "a"
            class Third(object):
                __slots__ = deque(["a", "b", "c"])
            class Fourth(object):
                __slots__ = {"a": "a", "b": "b"}
            class Fifth(object):
                __slots__ = list
            class Sixth(object):
                __slots__ = ""
            class Seventh(object):
                __slots__ = dedent.__name__
            class Eight(object):
                __slots__ = ("parens")
            class Ninth(object):
                pass
            class Ten(object):
                __slots__ = dict({"a": "b", "c": "d"})
        """)
        first = astroid['First']
        first_slots = first.slots()
        self.assertEqual(len(first_slots), 2)
        self.assertIsInstance(first_slots[0], nodes.Const)
        self.assertIsInstance(first_slots[1], nodes.Const)
        self.assertEqual(first_slots[0].value, "a")
        self.assertEqual(first_slots[1].value, "b")

        second_slots = astroid['Second'].slots()
        self.assertEqual(len(second_slots), 1)
        self.assertIsInstance(second_slots[0], nodes.Const)
        self.assertEqual(second_slots[0].value, "a")

        third_slots = astroid['Third'].slots()
        self.assertIsNone(third_slots)

        fourth_slots = astroid['Fourth'].slots()
        self.assertEqual(len(fourth_slots), 2)
        self.assertIsInstance(fourth_slots[0], nodes.Const)
        self.assertIsInstance(fourth_slots[1], nodes.Const)
        self.assertEqual(fourth_slots[0].value, "a")
        self.assertEqual(fourth_slots[1].value, "b")

        fifth_slots = astroid['Fifth'].slots()
        self.assertIsNone(fifth_slots)

        sixth_slots = astroid['Sixth'].slots()
        self.assertIsNone(sixth_slots)

        seventh_slots = astroid['Seventh'].slots()
        self.assertIsNone(seventh_slots)

        eight_slots = astroid['Eight'].slots()
        self.assertEqual(len(eight_slots), 1)
        self.assertIsInstance(eight_slots[0], nodes.Const)
        self.assertEqual(eight_slots[0].value, "parens")

        self.assertIsNone(astroid['Ninth'].slots())

        tenth_slots = astroid['Ten'].slots()
        self.assertEqual(len(tenth_slots), 2)
        self.assertEqual(
            [slot.value for slot in tenth_slots],
            ["a", "c"])

    @test_utils.require_version(maxver='3.0')
    def test_slots_py2(self):
        module = test_utils.build_module("""
        class UnicodeSlots(object):
            __slots__ = (u"a", u"b", "c")
        """)
        slots = module['UnicodeSlots'].slots()
        self.assertEqual(len(slots), 3)
        self.assertEqual(slots[0].value, "a")
        self.assertEqual(slots[1].value, "b")
        self.assertEqual(slots[2].value, "c")

    @test_utils.require_version(maxver='3.0')
    def test_slots_py2_not_implemented(self):
        module = test_utils.build_module("""
        class OldStyle:
            __slots__ = ("a", "b")
        """)
        msg = "The concept of slots is undefined for old-style classes."
        with self.assertRaises(NotImplementedError) as cm:
            module['OldStyle'].slots()
        self.assertEqual(str(cm.exception), msg)

    def assertEqualMro(self, klass, expected_mro):
        self.assertEqual(
            [member.name for member in klass.mro()],
            expected_mro)

    @test_utils.require_version(maxver='3.0')
    def test_no_mro_for_old_style(self):
        node = test_utils.extract_node("""
        class Old: pass""")
        with self.assertRaises(NotImplementedError) as cm:
            node.mro()
        self.assertEqual(str(cm.exception), "Could not obtain mro for "
                                            "old-style classes.")

    def test_mro(self):
        astroid = test_utils.build_module("""
        class C(object): pass
        class D(dict, C): pass

        class A1(object): pass
        class B1(A1): pass
        class C1(A1): pass
        class D1(B1, C1): pass
        class E1(C1, B1): pass
        class F1(D1, E1): pass
        class G1(E1, D1): pass

        class Boat(object): pass
        class DayBoat(Boat): pass
        class WheelBoat(Boat): pass
        class EngineLess(DayBoat): pass
        class SmallMultihull(DayBoat): pass
        class PedalWheelBoat(EngineLess, WheelBoat): pass
        class SmallCatamaran(SmallMultihull): pass
        class Pedalo(PedalWheelBoat, SmallCatamaran): pass

        class OuterA(object):
            class Inner(object):
                pass
        class OuterB(OuterA):
            class Inner(OuterA.Inner):
                pass
        class OuterC(OuterA):
            class Inner(OuterA.Inner):
                pass
        class OuterD(OuterC):
            class Inner(OuterC.Inner, OuterB.Inner):
                pass
        
        """)
        self.assertEqualMro(astroid['D'], ['D', 'dict', 'C', 'object'])
        self.assertEqualMro(astroid['D1'], ['D1', 'B1', 'C1', 'A1', 'object'])
        self.assertEqualMro(astroid['E1'], ['E1', 'C1', 'B1', 'A1', 'object'])
        with self.assertRaises(ResolveError) as cm:
            astroid['F1'].mro()
        self.assertEqual(str(cm.exception),
                         "Cannot create a consistent method resolution order "
                         "for bases (B1, C1, A1, object), "
                         "(C1, B1, A1, object)")

        with self.assertRaises(ResolveError) as cm:
            astroid['G1'].mro()
        self.assertEqual(str(cm.exception),
                         "Cannot create a consistent method resolution order "
                         "for bases (C1, B1, A1, object), "
                         "(B1, C1, A1, object)")

        self.assertEqualMro(
            astroid['PedalWheelBoat'],
            ["PedalWheelBoat", "EngineLess",
             "DayBoat", "WheelBoat", "Boat", "object"])

        self.assertEqualMro(
            astroid["SmallCatamaran"],
            ["SmallCatamaran", "SmallMultihull", "DayBoat", "Boat", "object"])

        self.assertEqualMro(
            astroid["Pedalo"],
            ["Pedalo", "PedalWheelBoat", "EngineLess", "SmallCatamaran",
             "SmallMultihull", "DayBoat", "WheelBoat", "Boat", "object"])

        self.assertEqualMro(
            astroid['OuterD']['Inner'],
            ['Inner', 'Inner', 'Inner', 'Inner', 'object'])


if __name__ == '__main__':
    unittest.main()
