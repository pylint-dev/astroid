# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER

"""tests for specific behaviour of astroid nodes
"""
import os
import sys
import textwrap
import unittest
import warnings

import six

import astroid
from astroid import builder
from astroid import context as contextmod
from astroid import exceptions
from astroid.tree import node_classes
from astroid import nodes
from astroid import parse
from astroid import raw_building
from astroid.interpreter import runtimeabc
from astroid.interpreter import objects
from astroid.interpreter import util as inferenceutil
from astroid import util
from astroid import test_utils
from astroid import transforms
from astroid.tests import resources
from astroid.tree import treeabc


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

    @test_utils.require_version(minver='3.0')
    def test_func_signature_issue_185(self):
        code = textwrap.dedent('''
        def test(a, b, c=42, *, x=42, **kwargs):
            print(a, b, c, args)
        ''')
        node = parse(code)
        self.assertEqual(node.as_string().strip(), code.strip())

    def test_as_string_for_list_containing_uninferable(self):
        node = test_utils.extract_node('''
        def foo():
            bar = [arg] * 1
        ''')
        binop = node.body[0].value
        inferred = next(binop.infer())
        self.assertEqual(inferred.as_string(), '[Uninferable]')
        self.assertEqual(binop.as_string(), '([arg]) * (1)')

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

    maxDiff = None
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

    def test_do_import_module_works_for_all(self):
        import_from, import_ = test_utils.extract_node('''
        from collections import deque #@
        import collections #@
        ''')
        inferred = inferenceutil.do_import_module(import_from, 'collections')
        self.assertIsInstance(inferred, nodes.Module)
        self.assertEqual(inferred.name, 'collections')
        inferred = inferenceutil.do_import_module(import_, 'collections')
        self.assertIsInstance(inferred, nodes.Module)
        self.assertEqual(inferred.name, 'collections')

    def test_import_self_resolve(self):
        myos = next(self.module2.igetattr('myos'))
        self.assertTrue(isinstance(myos, nodes.Module), myos)
        self.assertEqual(myos.name, 'os')
        self.assertEqual(myos.qname(), 'os')
        self.assertEqual(myos.pytype(), '%s.module' % BUILTINS)

    def test_from_self_resolve(self):
        namenode = next(self.module.igetattr('NameNode'))
        self.assertTrue(isinstance(namenode, nodes.ClassDef), namenode)
        self.assertEqual(namenode.root().name, 'astroid.tree.node_classes')
        self.assertEqual(namenode.qname(), 'astroid.tree.node_classes.Name')
        self.assertEqual(namenode.pytype(), '%s.type' % BUILTINS)
        abspath = next(self.module2.igetattr('abspath'))
        self.assertTrue(isinstance(abspath, nodes.FunctionDef), abspath)
        self.assertEqual(abspath.root().name, 'os.path')
        self.assertEqual(abspath.qname(), 'os.path.abspath')
        self.assertEqual(abspath.pytype(), '%s.function' % BUILTINS)

    def test_real_name(self):
        from_ = self.module['NameNode']
        self.assertEqual(inferenceutil.real_name(from_, 'NameNode'), 'Name')
        imp_ = self.module['os']
        self.assertEqual(inferenceutil.real_name(imp_, 'os'), 'os')
        self.assertRaises(exceptions.AttributeInferenceError,
                          inferenceutil.real_name, imp_, 'os.path')
        imp_ = self.module['NameNode']
        self.assertEqual(inferenceutil.real_name(imp_, 'NameNode'), 'Name')
        self.assertRaises(exceptions.AttributeInferenceError,
                          inferenceutil.real_name, imp_, 'Name')
        imp_ = self.module2['YO']
        self.assertEqual(inferenceutil.real_name(imp_, 'YO'), 'YO')
        self.assertRaises(exceptions.AttributeInferenceError,
                          inferenceutil.real_name, imp_, 'data')

    def test_as_string(self):
        ast = self.module['modutils']
        self.assertEqual(ast.as_string(), "from astroid import modutils")
        ast = self.module['NameNode']
        self.assertEqual(ast.as_string(), "from astroid.tree.node_classes import Name as NameNode")
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
        will catch this exception and yield and Uninferable instead.
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

        excs = list(inferenceutil.unpack_infer(handler_type))
        # The number of returned object can differ on Python 2
        # and Python 3. In one version, an additional item will
        # be returned, from the _pickle module, which is not
        # present in the other version.
        self.assertIsInstance(excs[0], nodes.ClassDef)
        self.assertEqual(excs[0].name, 'PickleError')
        self.assertIs(excs[-1], util.Uninferable)

    def test_absolute_import(self):
        astroid = resources.build_file('data/absimport.py')
        ctx = contextmod.InferenceContext()
        # will fail if absolute import failed
        ctx.lookupname = 'message'
        next(astroid['message'].infer(ctx))
        ctx.lookupname = 'email'
        m = next(astroid['email'].infer(ctx))
        self.assertFalse(m.source_file.startswith(os.path.join('data', 'email.py')))

    def test_more_absolute_import(self):
        astroid = resources.build_file('data/module1abs/__init__.py', 'data.module1abs')
        self.assertIn('sys', astroid.locals)


class CmpNodeTest(unittest.TestCase):
    def test_as_string(self):
        ast = abuilder.string_build("a == 2").body[0]
        self.assertEqual(ast.as_string(), "a == 2")


class ConstNodeTest(unittest.TestCase):

    def _test(self, value):
        node = raw_building.ast_from_object(value)
        self.assertIsInstance(node._proxied, (nodes.ClassDef, nodes.AssignName))
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
            with self.assertRaises(exceptions.AstroidBuildingError):
                builder.parse(code)
        else:
            ast = builder.parse(code)
            assign_true = ast['True']
            self.assertIsInstance(assign_true, nodes.AssignName)
            self.assertEqual(assign_true.name, "True")
            del_true = ast.body[2].targets[0]
            self.assertIsInstance(del_true, nodes.DelName)
            self.assertEqual(del_true.name, "True")


class ArgumentsNodeTC(unittest.TestCase):

    @unittest.skipIf(sys.version_info[:2] == (3, 3),
                     "Line numbering is broken on Python 3.3.")
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
        with self.assertRaises(exceptions.AttributeInferenceError):
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
        def lazy(): pass
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
            @lazy
            def decorated_with_lazy(self): return 42

        cls = A()
        builtin_property = cls.builtin_property
        abc_property = cls.abc_property
        cached_p = cls.cached_property
        reified = cls.reified
        not_prop = cls.not_prop
        lazy_prop = cls.lazy_prop
        lazyprop = cls.lazyprop
        decorated_with_lazy = cls.decorated_with_lazy
        ''')
        for prop in ('builtin_property', 'abc_property', 'cached_p', 'reified',
                     'lazy_prop', 'lazyprop', 'decorated_with_lazy'):
            inferred = next(ast[prop].infer())
            self.assertIsInstance(inferred, nodes.Const, prop)
            self.assertEqual(inferred.value, 42, prop)

        inferred = next(ast['not_prop'].infer())
        self.assertIsInstance(inferred, objects.BoundMethod)


@test_utils.require_version('3.5')
class Python35AsyncTest(unittest.TestCase):

    def test_async_await_keywords(self):
        async_def, async_for, async_with, await_node = test_utils.extract_node('''
        async def func(): #@
            async for i in range(10): #@
                f = __(await i)
            async with test(): #@
                pass
        ''')
        self.assertIsInstance(async_def, nodes.AsyncFunctionDef)
        self.assertIsInstance(async_for, nodes.AsyncFor)
        self.assertIsInstance(async_with, nodes.AsyncWith)
        self.assertIsInstance(await_node, nodes.Await)
        self.assertIsInstance(await_node.value, nodes.Name)

    def _test_await_async_as_string(self, code):
        ast_node = parse(code)
        self.assertEqual(ast_node.as_string().strip(), code.strip())

    def test_await_as_string(self):
        code = textwrap.dedent('''
        async def function():
            await 42
        ''')
        self._test_await_async_as_string(code)

    def test_asyncwith_as_string(self):
        code = textwrap.dedent('''
        async def function():
            async with (42):
                pass
        ''')
        self._test_await_async_as_string(code)

    def test_asyncfor_as_string(self):
        code = textwrap.dedent('''
        async def function():
            async for i in range(10):
                await 42
        ''')
        self._test_await_async_as_string(code)


class BaseTypesTest(unittest.TestCase):

    def test_concrete_issubclass(self):
        for node in nodes.ALL_NODE_CLASSES:
            name = node.__name__
            base_type = getattr(treeabc, name)
            self.assertTrue(issubclass(node, base_type), (node, base_type))

        self.assertTrue(issubclass(objects.Instance, runtimeabc.Instance))
        self.assertTrue(issubclass(objects.Generator, runtimeabc.Generator))
        self.assertTrue(issubclass(objects.BoundMethod, runtimeabc.BoundMethod))
        self.assertTrue(issubclass(objects.UnboundMethod, runtimeabc.UnboundMethod))


class ScopeTest(unittest.TestCase):

    def test_decorators(self):
        ast_node = test_utils.extract_node('''
        @test
        def foo(): pass
        ''')
        decorators = ast_node.decorators
        self.assertIsInstance(decorators.scope(), nodes.Module)
        self.assertEqual(decorators.scope(), decorators.root())

    def test_scoped_nodes(self):
        module = parse('''
        def function():
            pass
        genexp = (i for i in range(10))
        dictcomp = {i:i for i in range(10)}
        setcomp = {i for i in range(10)}
        listcomp = [i for i in range(10)]
        lambd = lambda x: x
        class classdef: pass
        ''')
        self.assertIsInstance(module.scope(), nodes.Module)
        self.assertIsInstance(module['genexp'].parent.value.scope(), nodes.GeneratorExp)
        self.assertIsInstance(module['dictcomp'].parent.value.scope(), nodes.DictComp)
        self.assertIsInstance(module['setcomp'].parent.value.scope(), nodes.SetComp)
        self.assertIsInstance(module['lambd'].parent.value.scope(), nodes.Lambda)
        self.assertIsInstance(next(module['function'].infer()).scope(), nodes.FunctionDef)
        self.assertIsInstance(next(module['classdef'].infer()).scope(), nodes.ClassDef)

        if six.PY3:
            self.assertIsInstance(module['listcomp'].parent.value.scope(), nodes.ListComp)
        else:
            self.assertIsInstance(module['listcomp'].parent.value.scope(), nodes.Module)

    def test_scope_of_default_argument_value(self):
        node = test_utils.extract_node('''
        def test(a=__(b)):
            pass
        ''')
        scope = node.scope()
        self.assertIsInstance(scope, nodes.Module)

    @test_utils.require_version(minver='3.0')
    def test_scope_of_default_keyword_argument_value(self):
        node = test_utils.extract_node('''
        def test(*, b=__(c)):
            pass
        ''')
        scope = node.scope()
        self.assertIsInstance(scope, nodes.Module)

    @test_utils.require_version(minver='3.0')
    def test_scope_of_annotations(self):
        ast_nodes = test_utils.extract_node('''
        def test(a: __(b), *args:__(f), c:__(d)=4, **kwargs: _(l))->__(x):
            pass
        ''')
        for node in ast_nodes:
            scope = node.scope()
            self.assertIsInstance(scope, nodes.Module)

    def test_scope_of_list_comprehension_target_composite_nodes(self):
        ast_node = test_utils.extract_node('''
        [i for data in __([DATA1, DATA2]) for i in data]
        ''')
        node = ast_node.elts[0]
        scope = node.scope()
        self.assertIsInstance(scope, nodes.Module)

    def test_scope_of_nested_list_comprehensions(self):
        ast_node = test_utils.extract_node('''
        [1 for data in DATA for x in __(data)]
        ''')
        scope = ast_node.scope()
        if six.PY2:
            self.assertIsInstance(scope, nodes.Module)
        else:
            self.assertIsInstance(scope, nodes.ListComp)

    def test_scope_of_list_comprehension_targets(self):
        ast_node = test_utils.extract_node('''
        [1 for data in DATA]
        ''')
        # target is `data` from the list comprehension
        target = ast_node.generators[0].target
        scope = target.scope()
        if six.PY2:
            self.assertIsInstance(scope, nodes.Module)
        else:
            self.assertIsInstance(scope, nodes.ListComp)

    def test_scope_of_list_comprehension_value(self):
        ast_node = test_utils.extract_node('''
        [__(i) for i in DATA]
        ''')
        scope = ast_node.scope()
        if six.PY3:
            self.assertIsInstance(scope, nodes.ListComp)
        else:
            self.assertIsInstance(scope, nodes.Module)

    def test_scope_of_dict_comprehension(self):        
        ast_nodes = test_utils.extract_node('''
        {i: __(j) for (i, j) in DATA}
        {i:j for (i, j) in __(DATA)}
        ''')
        elt_scope = ast_nodes[0].scope()
        self.assertIsInstance(elt_scope, nodes.DictComp)
        iter_scope = ast_nodes[1].scope()
        self.assertIsInstance(iter_scope, nodes.Module)

        ast_node = test_utils.extract_node('''
        {i:1 for i in DATA}''')
        target = ast_node.generators[0].target
        target_scope = target.scope()
        self.assertIsInstance(target_scope, nodes.DictComp)

    def test_scope_elt_of_generator_exp(self):
        ast_node = test_utils.extract_node('''
        list(__(i) for i in range(10))
        ''')
        scope = ast_node.scope()
        self.assertIsInstance(scope, nodes.GeneratorExp)
        

class ContextTest(unittest.TestCase):

    def test_subscript_load(self):
        node = test_utils.extract_node('f[1]')
        self.assertIs(node.ctx, astroid.Load)

    def test_subscript_del(self):
        node = test_utils.extract_node('del f[1]')
        self.assertIs(node.targets[0].ctx, astroid.Del)

    def test_subscript_store(self):
        node = test_utils.extract_node('f[1] = 2')
        subscript = node.targets[0]
        self.assertIs(subscript.ctx, astroid.Store)

    def test_list_load(self):
        node = test_utils.extract_node('[]')
        self.assertIs(node.ctx, astroid.Load)

    def test_list_del(self):
        node = test_utils.extract_node('del []')
        self.assertIs(node.targets[0].ctx, astroid.Del)

    def test_list_store(self):
        with self.assertRaises(exceptions.AstroidSyntaxError):
            test_utils.extract_node('[0] = 2')

    def test_tuple_load(self):
        node = test_utils.extract_node('(1, )')
        self.assertIs(node.ctx, astroid.Load)

    def test_tuple_store(self):
        with self.assertRaises(exceptions.AstroidSyntaxError):
            test_utils.extract_node('(1, ) = 3')

    @test_utils.require_version(minver='3.5')
    def test_starred_load(self):
        node = test_utils.extract_node('a = *b')
        starred = node.value
        self.assertIs(starred.ctx, astroid.Load)

    @test_utils.require_version(minver='3.0')
    def test_starred_store(self):
        node = test_utils.extract_node('a, *b = 1, 2')
        starred = node.targets[0].elts[1]
        self.assertIs(starred.ctx, astroid.Store) 
        

class FunctionTest(unittest.TestCase):

    def test_function_not_on_top_of_lambda(self):
        lambda_, function_ = test_utils.extract_node('''
        lambda x: x #@
        def func(): pass #@
        ''')
        self.assertNotIsInstance(lambda_, astroid.FunctionDef)
        self.assertNotIsInstance(function_, astroid.Lambda)


class DictTest(unittest.TestCase):

    def test_keys_values_items(self):
        node = test_utils.extract_node('''
        {1: 2, 2:3}
        ''')
        self.assertEqual([key.value for key in node.keys], [1, 2])
        self.assertEqual([value.value for value in node.values], [2, 3])
        self.assertEqual([(key.value, value.value) for (key, value) in node.items],
                         [(1, 2), (2, 3)])


class ParameterTest(unittest.TestCase):

    def _variadics_test_helper(self, vararg_lineno, vararg_col_offset,
                               kwarg_lineno, kwarg_col_offset):
        node = test_utils.extract_node('''
        def test(*args, **kwargs): pass
        ''')
        args = node.args
        self.assertIsInstance(args.vararg, astroid.Parameter)
        self.assertEqual(args.vararg.lineno, vararg_lineno)
        self.assertEqual(args.vararg.col_offset, vararg_col_offset)
        self.assertIsInstance(args.kwarg, astroid.Parameter)
        self.assertEqual(args.kwarg.lineno, kwarg_lineno)
        self.assertEqual(args.kwarg.col_offset, kwarg_col_offset)

    @unittest.skipUnless(sys.version_info[:2] < (3, 5),
                         "variadics support lineno & col_offset in 3.5+")
    def test_no_lineno_for_variadics(self):
        self._variadics_test_helper(vararg_lineno=None, vararg_col_offset=None,
                                    kwarg_lineno=None, kwarg_col_offset=None)

    @unittest.skipUnless(sys.version_info[:2] >= (3, 5),
                         "variadics support lineno & col_offset in 3.5+")
    def test_no_lineno_for_variadics(self):
        self._variadics_test_helper(vararg_lineno=2, vararg_col_offset=10,
                                    kwarg_lineno=2, kwarg_col_offset=18)


if __name__ == '__main__':
    unittest.main()
