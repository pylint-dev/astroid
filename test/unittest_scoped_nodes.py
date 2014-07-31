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

from __future__ import with_statement

import sys
from os.path import join, abspath, dirname
from textwrap import dedent

from logilab.common.testlib import TestCase, unittest_main, require_version

from astroid import YES, builder, nodes, scoped_nodes, \
     InferenceError, NotFoundError, NoDefault
from astroid.bases import BUILTINS, Instance, BoundMethod, UnboundMethod
from astroid.test_utils import extract_node

abuilder = builder.AstroidBuilder()
DATA = join(dirname(abspath(__file__)), 'data')
REGRTEST_DATA = join(dirname(abspath(__file__)), 'regrtest_data')
MODULE = abuilder.file_build(join(DATA, 'module.py'), 'data.module')
MODULE2 = abuilder.file_build(join(DATA, 'module2.py'), 'data.module2')
NONREGR = abuilder.file_build(join(DATA, 'nonregr.py'), 'data.nonregr')

PACK = abuilder.file_build(join(DATA, '__init__.py'), 'data')
PY3K = sys.version_info >= (3, 0)

def _test_dict_interface(self, node, test_attr):
    self.assertIs(node[test_attr], node[test_attr])
    self.assertIn(test_attr, node)
    node.keys()
    node.values()
    node.items()
    iter(node)


class ModuleNodeTC(TestCase):

    def test_special_attributes(self):
        self.assertEqual(len(MODULE.getattr('__name__')), 1)
        self.assertIsInstance(MODULE.getattr('__name__')[0], nodes.Const)
        self.assertEqual(MODULE.getattr('__name__')[0].value, 'data.module')
        self.assertEqual(len(MODULE.getattr('__doc__')), 1)
        self.assertIsInstance(MODULE.getattr('__doc__')[0], nodes.Const)
        self.assertEqual(MODULE.getattr('__doc__')[0].value, 'test module for astroid\n')
        self.assertEqual(len(MODULE.getattr('__file__')), 1)
        self.assertIsInstance(MODULE.getattr('__file__')[0], nodes.Const)
        self.assertEqual(MODULE.getattr('__file__')[0].value, join(DATA, 'module.py'))
        self.assertEqual(len(MODULE.getattr('__dict__')), 1)
        self.assertIsInstance(MODULE.getattr('__dict__')[0], nodes.Dict)
        self.assertRaises(NotFoundError, MODULE.getattr, '__path__')
        self.assertEqual(len(PACK.getattr('__path__')), 1)
        self.assertIsInstance(PACK.getattr('__path__')[0], nodes.List)

    def test_dict_interface(self):
        _test_dict_interface(self, MODULE, 'YO')

    def test_getattr(self):
        yo = MODULE.getattr('YO')[0]
        self.assertIsInstance(yo, nodes.Class)
        self.assertEqual(yo.name, 'YO')
        red = MODULE.igetattr('redirect').next()
        self.assertIsInstance(red, nodes.Function)
        self.assertEqual(red.name, 'four_args')
        pb = MODULE.igetattr('pb').next()
        self.assertIsInstance(pb, nodes.Class)
        self.assertEqual(pb.name, 'ProgressBar')
        # resolve packageredirection
        sys.path.insert(1, DATA)
        mod = abuilder.file_build(join(DATA, 'appl/myConnection.py'),
                                  'appl.myConnection')
        try:
            ssl = mod.igetattr('SSL1').next()
            cnx = ssl.igetattr('Connection').next()
            self.assertEqual(cnx.__class__, nodes.Class)
            self.assertEqual(cnx.name, 'Connection')
            self.assertEqual(cnx.root().name, 'SSL1.Connection1')
        finally:
            del sys.path[1]
        self.assertEqual(len(NONREGR.getattr('enumerate')), 2)
        # raise ResolveError
        self.assertRaises(InferenceError, MODULE.igetattr, 'YOAA')

    def test_wildard_import_names(self):
        m = abuilder.file_build(join(DATA, 'all.py'), 'all')
        self.assertEqual(m.wildcard_import_names(), ['Aaa', '_bla', 'name'])
        m = abuilder.file_build(join(DATA, 'notall.py'), 'notall')
        res = sorted(m.wildcard_import_names())
        self.assertEqual(res, ['Aaa', 'func', 'name', 'other'])

    def test_module_getattr(self):
        data = '''
appli = application
appli += 2
del appli
        '''
        astroid = abuilder.string_build(data, __name__, __file__)
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
        astroid = abuilder.string_build(data, 'package', join(REGRTEST_DATA, 'package', '__init__.py'))
        sys.path.insert(1, REGRTEST_DATA)
        try:
            m = astroid.import_module('', level=1)
            self.assertEqual(m.name, 'package')
            infered = list(astroid.igetattr('subpackage'))
            self.assertEqual(len(infered), 1)
            self.assertEqual(infered[0].name, 'package.subpackage')
        finally:
            del sys.path[1]


    def test_import_2(self):
        data = '''from . import subpackage as pouet'''
        astroid = abuilder.string_build(data, 'package', join(dirname(abspath(__file__)), 'regrtest_data', 'package', '__init__.py'))
        sys.path.insert(1, REGRTEST_DATA)
        try:
            m = astroid.import_module('', level=1)
            self.assertEqual(m.name, 'package')
            infered = list(astroid.igetattr('pouet'))
            self.assertEqual(len(infered), 1)
            self.assertEqual(infered[0].name, 'package.subpackage')
        finally:
            del sys.path[1]


    def test_file_stream_in_memory(self):
        data = '''irrelevant_variable is irrelevant'''
        astroid = abuilder.string_build(data, 'in_memory')
        self.assertEqual(astroid.file_stream.read().decode(), data)

    def test_file_stream_physical(self):
        path = join(DATA, 'all.py')
        astroid = abuilder.file_build(path, 'all')
        with open(path, 'rb') as file_io:
            self.assertEqual(astroid.file_stream.read(), file_io.read())


class FunctionNodeTC(TestCase):

    def test_special_attributes(self):
        func = MODULE2['make_class']
        self.assertEqual(len(func.getattr('__name__')), 1)
        self.assertIsInstance(func.getattr('__name__')[0], nodes.Const)
        self.assertEqual(func.getattr('__name__')[0].value, 'make_class')
        self.assertEqual(len(func.getattr('__doc__')), 1)
        self.assertIsInstance(func.getattr('__doc__')[0], nodes.Const)
        self.assertEqual(func.getattr('__doc__')[0].value, 'check base is correctly resolved to Concrete0')
        self.assertEqual(len(MODULE.getattr('__dict__')), 1)
        self.assertIsInstance(MODULE.getattr('__dict__')[0], nodes.Dict)

    def test_dict_interface(self):
        _test_dict_interface(self, MODULE['global_access'], 'local')

    def test_default_value(self):
        func = MODULE2['make_class']
        self.assertIsInstance(func.args.default_value('base'), nodes.Getattr)
        self.assertRaises(NoDefault, func.args.default_value, 'args')
        self.assertRaises(NoDefault, func.args.default_value, 'kwargs')
        self.assertRaises(NoDefault, func.args.default_value, 'any')
        #self.assertIsInstance(func.mularg_class('args'), nodes.Tuple)
        #self.assertIsInstance(func.mularg_class('kwargs'), nodes.Dict)
        #self.assertIsNone(func.mularg_class('base'))

    def test_navigation(self):
        function = MODULE['global_access']
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
        tree = abuilder.string_build(code)
        func = tree['nested_args']
        self.assertEqual(sorted(func.locals), ['a', 'b', 'c', 'd'])
        self.assertEqual(func.args.format_args(), 'a, (b, c, d)')

    def test_four_args(self):
        func = MODULE['four_args']
        #self.assertEqual(func.args.args, ['a', ('b', 'c', 'd')])
        local = sorted(func.keys())
        self.assertEqual(local, ['a', 'b', 'c', 'd'])
        self.assertEqual(func.type, 'function')

    def test_format_args(self):
        func = MODULE2['make_class']
        self.assertEqual(func.args.format_args(), 'any, base=data.module.YO, *args, **kwargs')
        func = MODULE['four_args']
        self.assertEqual(func.args.format_args(), 'a, b, c, d')

    def test_is_generator(self):
        self.assertTrue(MODULE2['generator'].is_generator())
        self.assertFalse(MODULE2['not_a_generator'].is_generator())
        self.assertFalse(MODULE2['make_class'].is_generator())

    def test_is_abstract(self):
        method = MODULE2['AbstractClass']['to_override']
        self.assertTrue(method.is_abstract(pass_is_abstract=False))
        self.assertEqual(method.qname(), 'data.module2.AbstractClass.to_override')
        self.assertEqual(method.pytype(), '%s.instancemethod' % BUILTINS)
        method = MODULE2['AbstractClass']['return_something']
        self.assertFalse(method.is_abstract(pass_is_abstract=False))
        # non regression : test raise "string" doesn't cause an exception in is_abstract
        func = MODULE2['raise_string']
        self.assertFalse(func.is_abstract(pass_is_abstract=False))

    def test_is_abstract_decorated(self):
        methods = extract_node("""
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
##         method = MODULE2['AbstractClass']['to_override']
##         self.assertEqual([str(term) for term in method.raises()],
##                           ["CallFunc(Name('NotImplementedError'), [], None, None)"] )

##     def test_returns(self):
##         method = MODULE2['AbstractClass']['return_something']
##         # use string comp since Node doesn't handle __cmp__
##         self.assertEqual([str(term) for term in method.returns()],
##                           ["Const('toto')", "Const(None)"])

    def test_lambda_pytype(self):
        data = '''
def f():
        g = lambda: None
        '''
        astroid = abuilder.string_build(data, __name__, __file__)
        g = list(astroid['f'].ilookup('g'))[0]
        self.assertEqual(g.pytype(), '%s.function' % BUILTINS)

    def test_lambda_qname(self):
        astroid = abuilder.string_build('''
lmbd = lambda: None
''', __name__, __file__)
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
        astroid = abuilder.string_build(data, __name__, __file__)
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
        astroid = abuilder.string_build(code, __name__, __file__)
        self.assertEqual(astroid['f'].argnames(), ['a', 'b', 'c', 'args', 'kwargs'])

    def test_return_nothing(self):
        """test infered value on a function with empty return"""
        data = '''
def func():
    return

a = func()
'''
        astroid = abuilder.string_build(data, __name__, __file__)
        call = astroid.body[1].value
        func_vals = call.infered()
        self.assertEqual(len(func_vals), 1)
        self.assertIsInstance(func_vals[0], nodes.Const)
        self.assertIsNone(func_vals[0].value)

    def test_func_instance_attr(self):
        """test instance attributes for functions"""
        data= """
def test():
    print(test.bar)

test.bar = 1
test()
        """
        astroid = abuilder.string_build(data, 'mod', __file__)
        func = astroid.body[2].value.func.infered()[0]
        self.assertIsInstance(func, nodes.Function)
        self.assertEqual(func.name, 'test')
        one = func.getattr('bar')[0].infered()[0]
        self.assertIsInstance(one, nodes.Const)
        self.assertEqual(one.value, 1)

    def test_type_builtin_descriptor_subclasses(self):
        astroid = abuilder.string_build(dedent("""
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
        """))
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
        astroid = abuilder.string_build(dedent("""
        def static_decorator(platform=None, order=50):
            def wrapper(f):
                f.cgm_module = True
                f.cgm_module_order = order
                f.cgm_module_platform = platform
                return staticmethod(f)
            return wrapper

        def classmethod_decorator(platform=None):
            def wrapper(f):
                f.platform = platform
                return classmethod(f)
            return wrapper

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
            
        """))
        node = astroid.locals['SomeClass'][0]
        self.assertEqual(node.locals['static'][0].type,
                         'staticmethod')
        self.assertEqual(node.locals['classmethod'][0].type,
                         'classmethod')
        self.assertEqual(node.locals['not_so_static'][0].type,
                         'method')
        self.assertEqual(node.locals['not_so_classmethod'][0].type,
                         'method')


class ClassNodeTC(TestCase):

    def test_dict_interface(self):
        _test_dict_interface(self, MODULE['YOUPI'], 'method')

    def test_cls_special_attributes_1(self):
        cls = MODULE['YO']
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
        astroid = abuilder.string_build('''
class A: pass
class B: pass

A.__bases__ += (B,)
''', __name__, __file__)
        self.assertEqual(len(astroid['A'].getattr('__bases__')), 2)
        self.assertIsInstance(astroid['A'].getattr('__bases__')[0], nodes.Tuple)
        self.assertIsInstance(astroid['A'].getattr('__bases__')[1], nodes.AssAttr)

    def test_instance_special_attributes(self):
        for inst in (Instance(MODULE['YO']), nodes.List(), nodes.Const(1)):
            self.assertRaises(NotFoundError, inst.getattr, '__mro__')
            self.assertRaises(NotFoundError, inst.getattr, '__bases__')
            self.assertRaises(NotFoundError, inst.getattr, '__name__')
            self.assertEqual(len(inst.getattr('__dict__')), 1)
            self.assertEqual(len(inst.getattr('__doc__')), 1)

    def test_navigation(self):
        klass = MODULE['YO']
        self.assertEqual(klass.statement(), klass)
        l_sibling = klass.previous_sibling()
        self.assertTrue(isinstance(l_sibling, nodes.Function), l_sibling)
        self.assertEqual(l_sibling.name, 'global_access')
        r_sibling = klass.next_sibling()
        self.assertIsInstance(r_sibling, nodes.Class)
        self.assertEqual(r_sibling.name, 'YOUPI')

    def test_local_attr_ancestors(self):
        klass2 = MODULE['YOUPI']
        it = klass2.local_attr_ancestors('__init__')
        anc_klass = it.next()
        self.assertIsInstance(anc_klass, nodes.Class)
        self.assertEqual(anc_klass.name, 'YO')
        self.assertRaises(StopIteration, it.next)
        it = klass2.local_attr_ancestors('method')
        self.assertRaises(StopIteration, it.next)

    def test_instance_attr_ancestors(self):
        klass2 = MODULE['YOUPI']
        it = klass2.instance_attr_ancestors('yo')
        anc_klass = it.next()
        self.assertIsInstance(anc_klass, nodes.Class)
        self.assertEqual(anc_klass.name, 'YO')
        self.assertRaises(StopIteration, it.next)
        klass2 = MODULE['YOUPI']
        it = klass2.instance_attr_ancestors('member')
        self.assertRaises(StopIteration, it.next)

    def test_methods(self):
        klass2 = MODULE['YOUPI']
        methods = sorted([m.name for m in klass2.methods()])
        self.assertEqual(methods, ['__init__', 'class_method',
                                   'method', 'static_method'])
        methods = [m.name for m in klass2.mymethods()]
        methods.sort()
        self.assertEqual(methods, ['__init__', 'class_method',
                                   'method', 'static_method'])
        klass2 = MODULE2['Specialization']
        methods = [m.name for m in klass2.mymethods()]
        methods.sort()
        self.assertEqual(methods, [])
        method_locals = klass2.local_attr('method')
        self.assertEqual(len(method_locals), 1)
        self.assertEqual(method_locals[0].name, 'method')
        self.assertRaises(NotFoundError, klass2.local_attr, 'nonexistant')
        methods = [m.name for m in klass2.methods()]
        methods.sort()
        self.assertEqual(methods, ['__init__', 'class_method',
                                   'method', 'static_method'])

    #def test_rhs(self):
    #    my_dict = MODULE['MY_DICT']
    #    self.assertIsInstance(my_dict.rhs(), nodes.Dict)
    #    a = MODULE['YO']['a']
    #    value = a.rhs()
    #    self.assertIsInstance(value, nodes.Const)
    #    self.assertEqual(value.value, 1)

    def test_ancestors(self):
        klass = MODULE['YOUPI']
        ancs = [a.name for a in klass.ancestors()]
        self.assertEqual(ancs, ['YO'])
        klass = MODULE2['Specialization']
        ancs = [a.name for a in klass.ancestors()]
        self.assertEqual(ancs, ['YOUPI', 'YO'])

    def test_type(self):
        klass = MODULE['YOUPI']
        self.assertEqual(klass.type, 'class')
        klass = MODULE2['Metaclass']
        self.assertEqual(klass.type, 'metaclass')
        klass = MODULE2['MyException']
        self.assertEqual(klass.type, 'exception')
        klass = MODULE2['MyIFace']
        self.assertEqual(klass.type, 'interface')
        klass = MODULE2['MyError']
        self.assertEqual(klass.type, 'exception')
        # the following class used to be detected as a metaclass
        # after the fix which used instance._proxied in .ancestors(),
        # when in fact it is a normal class
        klass = MODULE2['NotMetaclass']
        self.assertEqual(klass.type, 'class')

    def test_interfaces(self):
        for klass, interfaces in (('Concrete0', ['MyIFace']),
                                  ('Concrete1', ['MyIFace', 'AnotherIFace']),
                                  ('Concrete2', ['MyIFace', 'AnotherIFace']),
                                  ('Concrete23', ['MyIFace', 'AnotherIFace'])):
            klass = MODULE2[klass]
            self.assertEqual([i.name for i in klass.interfaces()],
                              interfaces)

    def test_concat_interfaces(self):
        astroid = abuilder.string_build('''
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
        eee = NONREGR['Ccc']['Eee']
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
        astroid = abuilder.string_build(data, __name__, __file__)
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
        astroid = abuilder.string_build(data, __name__, __file__)
        cls = astroid['WebAppObject']
        # test del statement not returned by getattr
        self.assertEqual(len(cls.getattr('appli')), 2)


    def test_instance_getattr(self):
        data =         '''
class WebAppObject(object):
    def __init__(self, application):
        self.appli = application
        self.appli += 2
        del self.appli
         '''
        astroid = abuilder.string_build(data, __name__, __file__)
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
        astroid = abuilder.string_build(data, __name__, __file__)
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
        astroid = abuilder.string_build(data, __name__, __file__)
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
        astroid = abuilder.string_build(data)
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
        astroid = abuilder.string_build(data)
        self.assertEqual(astroid['g1'].fromlineno, 4)
        self.assertEqual(astroid['g1'].tolineno, 5)
        self.assertEqual(astroid['g2'].fromlineno, 9)
        self.assertEqual(astroid['g2'].tolineno, 10)

    def test_simple_metaclass(self):
        if PY3K:
            self.skipTest('__metaclass__ syntax is python2-specific')
        astroid = abuilder.string_build(dedent("""
        class Test(object):
            __metaclass__ = type
        """))
        klass = astroid['Test']

        metaclass = klass.metaclass()
        self.assertIsInstance(metaclass, scoped_nodes.Class)
        self.assertEqual(metaclass.name, 'type')

    def test_metaclass_error(self):
        astroid = abuilder.string_build(dedent("""
        class Test(object):
            __metaclass__ = typ
        """))
        klass = astroid['Test']
        self.assertFalse(klass.metaclass())

    def test_metaclass_imported(self):
        if PY3K:
            self.skipTest('__metaclass__ syntax is python2-specific')
        astroid = abuilder.string_build(dedent("""
        from abc import ABCMeta
        class Test(object):
            __metaclass__ = ABCMeta
        """))
        klass = astroid['Test']

        metaclass = klass.metaclass()
        self.assertIsInstance(metaclass, scoped_nodes.Class)
        self.assertEqual(metaclass.name, 'ABCMeta')

    def test_metaclass_yes_leak(self):
        astroid = abuilder.string_build(dedent("""
        # notice `ab` instead of `abc`
        from ab import ABCMeta

        class Meta(object):
            __metaclass__ = ABCMeta
        """))
        klass = astroid['Meta']
        self.assertIsNone(klass.metaclass())

    def test_newstyle_and_metaclass_good(self):
        if PY3K:
            self.skipTest('__metaclass__ syntax is python2-specific')
        astroid = abuilder.string_build(dedent("""
        from abc import ABCMeta
        class Test:
            __metaclass__ = ABCMeta
        """))
        klass = astroid['Test']
        self.assertTrue(klass.newstyle)
        self.assertEqual(klass.metaclass().name, 'ABCMeta')
        astroid = abuilder.string_build(dedent("""
        from abc import ABCMeta
        __metaclass__ = ABCMeta
        class Test:
            pass
        """))
        klass = astroid['Test']
        self.assertTrue(klass.newstyle)
        self.assertEqual(klass.metaclass().name, 'ABCMeta')

    def test_nested_metaclass(self):
        if PY3K:
            self.skipTest('__metaclass__ syntax is python2-specific')
        astroid = abuilder.string_build(dedent("""
        from abc import ABCMeta
        class A(object):
            __metaclass__ = ABCMeta
            class B: pass

        __metaclass__ = ABCMeta
        class C:
           __metaclass__ = type
           class D: pass
        """))
        a = astroid['A']
        b = a.locals['B'][0]
        c = astroid['C']
        d = c.locals['D'][0]
        self.assertEqual(a.metaclass().name, 'ABCMeta')
        self.assertFalse(b.newstyle)
        self.assertIsNone(b.metaclass())
        self.assertEqual(c.metaclass().name, 'type')
        self.assertEqual(d.metaclass().name, 'ABCMeta')

    def test_parent_metaclass(self):
        if PY3K:
            self.skipTest('__metaclass__ syntax is python2-specific')
        astroid = abuilder.string_build(dedent("""
        from abc import ABCMeta
        class Test:
            __metaclass__ = ABCMeta
        class SubTest(Test): pass
        """))
        klass = astroid['SubTest']
        self.assertTrue(klass.newstyle)
        metaclass = klass.metaclass()
        self.assertIsInstance(metaclass, scoped_nodes.Class)
        self.assertEqual(metaclass.name, 'ABCMeta')

    def test_metaclass_ancestors(self):
        if PY3K:
            self.skipTest('__metaclass__ syntax is python2-specific')
        astroid = abuilder.string_build(dedent("""
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
        """))
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
        klass = extract_node("""
        def with_metaclass(meta, base=object):
            return meta("NewBase", (base, ), {})

        class ClassWithMeta(with_metaclass(type)): #@
            pass
        """)
        self.assertEqual(
            ['NewBase', 'object'],
            [base.name for base in klass.ancestors()])

    def test_nonregr_infer_callresult(self):
        astroid = abuilder.string_build(dedent("""
        class Delegate(object):
            def __get__(self, obj, cls):
                return getattr(obj._subject, self.attribute)

        class CompositeBuilder(object):
            __call__ = Delegate()

        builder = CompositeBuilder(result, composite)
        tgts = builder()
        """))
        instance = astroid['tgts']
        # used to raise "'_Yes' object is not iterable", see
        # https://bitbucket.org/logilab/astroid/issue/17
        self.assertEqual(list(instance.infer()), [YES])

    def test_slots(self):
        astroid = abuilder.string_build(dedent("""
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
        """))
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
        self.assertEqual(third_slots, [])

        fourth_slots = astroid['Fourth'].slots()
        self.assertEqual(len(fourth_slots), 2)
        self.assertIsInstance(fourth_slots[0], nodes.Const)
        self.assertIsInstance(fourth_slots[1], nodes.Const)
        self.assertEqual(fourth_slots[0].value, "a")
        self.assertEqual(fourth_slots[1].value, "b")

        fifth_slots = astroid['Fifth'].slots()
        self.assertEqual(fifth_slots, [])

        sixth_slots = astroid['Sixth'].slots()
        self.assertEqual(sixth_slots, [])

        seventh_slots = astroid['Seventh'].slots()
        self.assertEqual(len(seventh_slots), 0)

        eight_slots = astroid['Eight'].slots()
        self.assertEqual(len(eight_slots), 1)
        self.assertIsInstance(eight_slots[0], nodes.Const)
        self.assertEqual(eight_slots[0].value, "parens")


__all__ = ('ModuleNodeTC', 'ImportNodeTC', 'FunctionNodeTC', 'ClassNodeTC')

if __name__ == '__main__':
    unittest_main()
