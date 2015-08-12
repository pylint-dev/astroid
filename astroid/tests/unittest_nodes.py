# copyright 2003-2013 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
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
"""tests for specific behaviour of astroid nodes
"""
import os
import sys
import textwrap
import unittest

import six

from astroid import bases
from astroid import builder
from astroid import context as contextmod
from astroid import exceptions
from astroid import node_classes
from astroid import nodes
from astroid import util
from astroid import test_utils
from astroid.tests import resources


abuilder = builder.AstroidBuilder()
BUILTINS = six.moves.builtins.__name__


class AsStringTest(resources.SysPathSetup, unittest.TestCase):

    def test_tuple_as_string(self):
        def build(string):
            return abuilder.string_build(string).body[0].value

        self.assertEqual(build('1,').as_string(), '(1, )')
        self.assertEqual(build('1, 2, 3').as_string(), '(1, 2, 3)')
        self.assertEqual(build('(1, )').as_string(), '(1, )')
        self.assertEqual(build('1, 2, 3').as_string(), '(1, 2, 3)')

    def test_frozenset_as_string(self):
        nodes = test_utils.extract_node('''
        frozenset((1, 2, 3)) #@
        frozenset({1, 2, 3}) #@
        frozenset([1, 2, 3,]) #@

        frozenset(None) #@
        frozenset(1) #@
        ''')
        nodes = [next(node.infer()) for node in nodes]

        self.assertEqual(nodes[0].as_string(), 'frozenset((1, 2, 3))')
        self.assertEqual(nodes[1].as_string(), 'frozenset({1, 2, 3})')
        self.assertEqual(nodes[2].as_string(), 'frozenset([1, 2, 3])')

        self.assertNotEqual(nodes[3].as_string(), 'frozenset(None)')
        self.assertNotEqual(nodes[4].as_string(), 'frozenset(1)')

    def test_varargs_kwargs_as_string(self):
        ast = abuilder.string_build('raise_string(*args, **kwargs)').body[0]
        self.assertEqual(ast.as_string(), 'raise_string(*args, **kwargs)')

    def test_module_as_string(self):
        """check as_string on a whole module prepared to be returned identically
        """
        module = resources.build_file('data/module.py', 'data.module')
        with open(resources.find('data/module.py'), 'r') as fobj:
            self.assertMultiLineEqual(module.as_string(), fobj.read())

    def test_module2_as_string(self):
        """check as_string on a whole module prepared to be returned identically
        """
        module2 = resources.build_file('data/module2.py', 'data.module2')
        with open(resources.find('data/module2.py'), 'r') as fobj:
            self.assertMultiLineEqual(module2.as_string(), fobj.read())

    def test_as_string(self):
        """check as_string for python syntax >= 2.7"""
        code = '''one_two = {1, 2}
b = {v: k for (k, v) in enumerate('string')}
cdd = {k for k in b}\n\n'''
        ast = abuilder.string_build(code)
        self.assertMultiLineEqual(ast.as_string(), code)

    @test_utils.require_version('3.0')
    def test_3k_as_string(self):
        """check as_string for python 3k syntax"""
        code = '''print()

def function(var):
    nonlocal counter
    try:
        hello
    except NameError as nexc:
        (*hell, o) = b'hello'
        raise AttributeError from nexc
\n'''
        ast = abuilder.string_build(code)
        self.assertEqual(ast.as_string(), code)

    @test_utils.require_version('3.0')
    @unittest.expectedFailure
    def test_3k_annotations_and_metaclass(self):
        code_annotations = textwrap.dedent('''
        def function(var:int):
            nonlocal counter

        class Language(metaclass=Natural):
            """natural language"""
        ''')

        ast = abuilder.string_build(code_annotations)
        self.assertEqual(ast.as_string(), code_annotations)

    def test_ellipsis(self):
        ast = abuilder.string_build('a[...]').body[0]
        self.assertEqual(ast.as_string(), 'a[...]')

    def test_slices(self):
        for code in ('a[0]', 'a[1:3]', 'a[:-1:step]', 'a[:,newaxis]',
                     'a[newaxis,:]', 'del L[::2]', 'del A[1]', 'del Br[:]'):
            ast = abuilder.string_build(code).body[0]
            self.assertEqual(ast.as_string(), code)

    def test_slice_and_subscripts(self):
        code = """a[:1] = bord[2:]
a[:1] = bord[2:]
del bree[3:d]
bord[2:]
del av[d::f], a[df:]
a[:1] = bord[2:]
del SRC[::1,newaxis,1:]
tous[vals] = 1010
del thousand[key]
del a[::2], a[:-1:step]
del Fee.form[left:]
aout.vals = miles.of_stuff
del (ccok, (name.thing, foo.attrib.value)), Fee.form[left:]
if all[1] == bord[0:]:
    pass\n\n"""
        ast = abuilder.string_build(code)
        self.assertEqual(ast.as_string(), code)


class _NodeTest(unittest.TestCase):
    """test transformation of If Node"""
    CODE = None

    @property
    def astroid(self):
        try:
            return self.__class__.__dict__['CODE_Astroid']
        except KeyError:
            astroid = builder.parse(self.CODE)
            self.__class__.CODE_Astroid = astroid
            return astroid


class IfNodeTest(_NodeTest):
    """test transformation of If Node"""
    CODE = """
        if 0:
            print()

        if True:
            print()
        else:
            pass

        if "":
            print()
        elif []:
            raise

        if 1:
            print()
        elif True:
            print()
        elif func():
            pass
        else:
            raise
    """

    def test_if_elif_else_node(self):
        """test transformation for If node"""
        self.assertEqual(len(self.astroid.body), 4)
        for stmt in self.astroid.body:
            self.assertIsInstance(stmt, nodes.If)
        self.assertFalse(self.astroid.body[0].orelse)  # simple If
        self.assertIsInstance(self.astroid.body[1].orelse[0], nodes.Pass)  # If / else
        self.assertIsInstance(self.astroid.body[2].orelse[0], nodes.If)  # If / elif
        self.assertIsInstance(self.astroid.body[3].orelse[0].orelse[0], nodes.If)

    def test_block_range(self):
        # XXX ensure expected values
        self.assertEqual(self.astroid.block_range(1), (0, 22))
        self.assertEqual(self.astroid.block_range(10), (0, 22))  # XXX (10, 22) ?
        self.assertEqual(self.astroid.body[1].block_range(5), (5, 6))
        self.assertEqual(self.astroid.body[1].block_range(6), (6, 6))
        self.assertEqual(self.astroid.body[1].orelse[0].block_range(7), (7, 8))
        self.assertEqual(self.astroid.body[1].orelse[0].block_range(8), (8, 8))


class TryExceptNodeTest(_NodeTest):
    CODE = """
        try:
            print ('pouet')
        except IOError:
            pass
        except UnicodeError:
            print()
        else:
            print()
    """

    def test_block_range(self):
        # XXX ensure expected values
        self.assertEqual(self.astroid.body[0].block_range(1), (1, 8))
        self.assertEqual(self.astroid.body[0].block_range(2), (2, 2))
        self.assertEqual(self.astroid.body[0].block_range(3), (3, 8))
        self.assertEqual(self.astroid.body[0].block_range(4), (4, 4))
        self.assertEqual(self.astroid.body[0].block_range(5), (5, 5))
        self.assertEqual(self.astroid.body[0].block_range(6), (6, 6))
        self.assertEqual(self.astroid.body[0].block_range(7), (7, 7))
        self.assertEqual(self.astroid.body[0].block_range(8), (8, 8))


class TryFinallyNodeTest(_NodeTest):
    CODE = """
        try:
            print ('pouet')
        finally:
            print ('pouet')
    """

    def test_block_range(self):
        # XXX ensure expected values
        self.assertEqual(self.astroid.body[0].block_range(1), (1, 4))
        self.assertEqual(self.astroid.body[0].block_range(2), (2, 2))
        self.assertEqual(self.astroid.body[0].block_range(3), (3, 4))
        self.assertEqual(self.astroid.body[0].block_range(4), (4, 4))


class TryExceptFinallyNodeTest(_NodeTest):
    CODE = """
        try:
            print('pouet')
        except Exception:
            print ('oops')
        finally:
            print ('pouet')
    """

    def test_block_range(self):
        # XXX ensure expected values
        self.assertEqual(self.astroid.body[0].block_range(1), (1, 6))
        self.assertEqual(self.astroid.body[0].block_range(2), (2, 2))
        self.assertEqual(self.astroid.body[0].block_range(3), (3, 4))
        self.assertEqual(self.astroid.body[0].block_range(4), (4, 4))
        self.assertEqual(self.astroid.body[0].block_range(5), (5, 5))
        self.assertEqual(self.astroid.body[0].block_range(6), (6, 6))


@unittest.skipIf(six.PY3, "Python 2 specific test.")
class TryExcept2xNodeTest(_NodeTest):
    CODE = """
        try:
            hello
        except AttributeError, (retval, desc):
            pass
    """


    def test_tuple_attribute(self):
        handler = self.astroid.body[0].handlers[0]
        self.assertIsInstance(handler.name, nodes.Tuple)


class ImportNodeTest(resources.SysPathSetup, unittest.TestCase):
    def setUp(self):
        super(ImportNodeTest, self).setUp()
        self.module = resources.build_file('data/module.py', 'data.module')
        self.module2 = resources.build_file('data/module2.py', 'data.module2')

    def test_import_self_resolve(self):
        myos = next(self.module2.igetattr('myos'))
        self.assertTrue(isinstance(myos, nodes.Module), myos)
        self.assertEqual(myos.name, 'os')
        self.assertEqual(myos.qname(), 'os')
        self.assertEqual(myos.pytype(), '%s.module' % BUILTINS)

    def test_from_self_resolve(self):
        namenode = next(self.module.igetattr('NameNode'))
        self.assertTrue(isinstance(namenode, nodes.Class), namenode)
        self.assertEqual(namenode.root().name, 'astroid.node_classes')
        self.assertEqual(namenode.qname(), 'astroid.node_classes.Name')
        self.assertEqual(namenode.pytype(), '%s.type' % BUILTINS)
        abspath = next(self.module2.igetattr('abspath'))
        self.assertTrue(isinstance(abspath, nodes.Function), abspath)
        self.assertEqual(abspath.root().name, 'os.path')
        self.assertEqual(abspath.qname(), 'os.path.abspath')
        self.assertEqual(abspath.pytype(), '%s.function' % BUILTINS)

    def test_real_name(self):
        from_ = self.module['NameNode']
        self.assertEqual(from_.real_name('NameNode'), 'Name')
        imp_ = self.module['os']
        self.assertEqual(imp_.real_name('os'), 'os')
        self.assertRaises(exceptions.NotFoundError, imp_.real_name, 'os.path')
        imp_ = self.module['NameNode']
        self.assertEqual(imp_.real_name('NameNode'), 'Name')
        self.assertRaises(exceptions.NotFoundError, imp_.real_name, 'Name')
        imp_ = self.module2['YO']
        self.assertEqual(imp_.real_name('YO'), 'YO')
        self.assertRaises(exceptions.NotFoundError, imp_.real_name, 'data')

    def test_as_string(self):
        ast = self.module['modutils']
        self.assertEqual(ast.as_string(), "from astroid import modutils")
        ast = self.module['NameNode']
        self.assertEqual(ast.as_string(), "from astroid.node_classes import Name as NameNode")
        ast = self.module['os']
        self.assertEqual(ast.as_string(), "import os.path")
        code = """from . import here
from .. import door
from .store import bread
from ..cave import wine\n\n"""
        ast = abuilder.string_build(code)
        self.assertMultiLineEqual(ast.as_string(), code)

    def test_bad_import_inference(self):
        # Explication of bug
        '''When we import PickleError from nonexistent, a call to the infer
        method of this From node will be made by unpack_infer.
        inference.infer_from will try to import this module, which will fail and
        raise a InferenceException (by mixins.do_import_module). The infer_name
        will catch this exception and yield and YES instead.
        '''

        code = '''
            try:
                from pickle import PickleError
            except ImportError:
                from nonexistent import PickleError

            try:
                pass
            except PickleError:
                pass
        '''
        astroid = builder.parse(code)
        handler_type = astroid.body[1].handlers[0].type

        excs = list(node_classes.unpack_infer(handler_type))
        # The number of returned object can differ on Python 2
        # and Python 3. In one version, an additional item will
        # be returned, from the _pickle module, which is not
        # present in the other version.
        self.assertIsInstance(excs[0], nodes.Class)
        self.assertEqual(excs[0].name, 'PickleError')
        self.assertIs(excs[-1], util.YES)

    def test_absolute_import(self):
        astroid = resources.build_file('data/absimport.py')
        ctx = contextmod.InferenceContext()
        # will fail if absolute import failed
        ctx.lookupname = 'message'
        next(astroid['message'].infer(ctx))
        ctx.lookupname = 'email'
        m = next(astroid['email'].infer(ctx))
        self.assertFalse(m.file.startswith(os.path.join('data', 'email.py')))

    def test_more_absolute_import(self):
        astroid = resources.build_file('data/module1abs/__init__.py', 'data.module1abs')
        self.assertIn('sys', astroid.locals)


class CmpNodeTest(unittest.TestCase):
    def test_as_string(self):
        ast = abuilder.string_build("a == 2").body[0]
        self.assertEqual(ast.as_string(), "a == 2")


class ConstNodeTest(unittest.TestCase):

    def _test(self, value):
        node = nodes.const_factory(value)
        self.assertIsInstance(node._proxied, nodes.Class)
        self.assertEqual(node._proxied.name, value.__class__.__name__)
        self.assertIs(node.value, value)
        self.assertTrue(node._proxied.parent)
        self.assertEqual(node._proxied.root().name, value.__class__.__module__)

    def test_none(self):
        self._test(None)

    def test_bool(self):
        self._test(True)

    def test_int(self):
        self._test(1)

    def test_float(self):
        self._test(1.0)

    def test_complex(self):
        self._test(1.0j)

    def test_str(self):
        self._test('a')

    def test_unicode(self):
        self._test(u'a')


class NameNodeTest(unittest.TestCase):
    def test_assign_to_True(self):
        """test that True and False assignements don't crash"""
        code = """
            True = False
            def hello(False):
                pass
            del True
        """
        if sys.version_info >= (3, 0):
            with self.assertRaises(exceptions.AstroidBuildingException):
                builder.parse(code)
        else:
            ast = builder.parse(code)
            ass_true = ast['True']
            self.assertIsInstance(ass_true, nodes.AssName)
            self.assertEqual(ass_true.name, "True")
            del_true = ast.body[2].targets[0]
            self.assertIsInstance(del_true, nodes.DelName)
            self.assertEqual(del_true.name, "True")


class ArgumentsNodeTC(unittest.TestCase):
    def test_linenumbering(self):
        ast = builder.parse('''
            def func(a,
                b): pass
            x = lambda x: None
        ''')
        self.assertEqual(ast['func'].args.fromlineno, 2)
        self.assertFalse(ast['func'].args.is_statement)
        xlambda = next(ast['x'].infer())
        self.assertEqual(xlambda.args.fromlineno, 4)
        self.assertEqual(xlambda.args.tolineno, 4)
        self.assertFalse(xlambda.args.is_statement)
        if sys.version_info < (3, 0):
            self.assertEqual(ast['func'].args.tolineno, 3)
        else:
            self.skipTest('FIXME  http://bugs.python.org/issue10445 '
                          '(no line number on function args)')

    def test_builtin_fromlineno_missing(self):
        cls = test_utils.extract_node('''
        class Foo(Exception): #@
            pass
        ''')
        new = cls.getattr('__new__')[-1]
        self.assertEqual(new.args.fromlineno, 0)


class UnboundMethodNodeTest(unittest.TestCase):

    def test_no_super_getattr(self):
        # This is a test for issue
        # https://bitbucket.org/logilab/astroid/issue/91, which tests
        # that UnboundMethod doesn't call super when doing .getattr.

        ast = builder.parse('''
        class A(object):
            def test(self):
                pass
        meth = A.test
        ''')
        node = next(ast['meth'].infer())
        with self.assertRaises(exceptions.NotFoundError):
            node.getattr('__missssing__')
        name = node.getattr('__name__')[0]
        self.assertIsInstance(name, nodes.Const)
        self.assertEqual(name.value, 'test')


class BoundMethodNodeTest(unittest.TestCase):

    def test_is_property(self):
        ast = builder.parse('''
        import abc

        def cached_property():
            # Not a real decorator, but we don't care
            pass
        def reify():
            # Same as cached_property
            pass
        def lazy_property():
            pass
        def lazyproperty():
            pass
        class A(object):
            @property
            def builtin_property(self):
                return 42
            @abc.abstractproperty
            def abc_property(self):
                return 42
            @cached_property
            def cached_property(self): return 42
            @reify
            def reified(self): return 42
            @lazy_property
            def lazy_prop(self): return 42
            @lazyproperty
            def lazyprop(self): return 42
            def not_prop(self): pass

        cls = A()
        builtin_property = cls.builtin_property
        abc_property = cls.abc_property
        cached_p = cls.cached_property
        reified = cls.reified
        not_prop = cls.not_prop
        lazy_prop = cls.lazy_prop
        lazyprop = cls.lazyprop
        ''')
        for prop in ('builtin_property', 'abc_property', 'cached_p', 'reified',
                     'lazy_prop', 'lazyprop'):
            infered = next(ast[prop].infer())
            self.assertIsInstance(infered, nodes.Const, prop)
            self.assertEqual(infered.value, 42, prop)

        infered = next(ast['not_prop'].infer())
        self.assertIsInstance(infered, bases.BoundMethod)


if __name__ == '__main__':
    unittest.main()
