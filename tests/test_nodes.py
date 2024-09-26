# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Tests for specific behaviour of astroid nodes."""

from __future__ import annotations

import copy
import inspect
import os
import random
import sys
import textwrap
import unittest
from typing import Any

import pytest

import astroid
from astroid import (
    Uninferable,
    bases,
    builder,
    extract_node,
    nodes,
    parse,
    transforms,
    util,
)
from astroid.const import IS_PYPY, PY310_PLUS, PY312_PLUS, Context
from astroid.context import InferenceContext
from astroid.exceptions import (
    AstroidBuildingError,
    AstroidSyntaxError,
    AttributeInferenceError,
    ParentMissingError,
    StatementMissing,
)
from astroid.nodes.node_classes import (
    AssignAttr,
    AssignName,
    Attribute,
    Call,
    ImportFrom,
    Tuple,
)
from astroid.nodes.scoped_nodes import ClassDef, FunctionDef, GeneratorExp, Module
from tests.testdata.python3.recursion_error import LONG_CHAINED_METHOD_CALL

from . import resources

abuilder = builder.AstroidBuilder()


class AsStringTest(resources.SysPathSetup, unittest.TestCase):
    def test_tuple_as_string(self) -> None:
        def build(string: str) -> Tuple:
            return abuilder.string_build(string).body[0].value

        self.assertEqual(build("1,").as_string(), "(1, )")
        self.assertEqual(build("1, 2, 3").as_string(), "(1, 2, 3)")
        self.assertEqual(build("(1, )").as_string(), "(1, )")
        self.assertEqual(build("1, 2, 3").as_string(), "(1, 2, 3)")

    def test_func_signature_issue_185(self) -> None:
        code = textwrap.dedent(
            """
        def test(a, b, c=42, *, x=42, **kwargs):
            print(a, b, c, args)
        """
        )
        node = parse(code)
        self.assertEqual(node.as_string().strip(), code.strip())

    def test_as_string_for_list_containing_uninferable(self) -> None:
        node = builder.extract_node(
            """
        def foo():
            bar = [arg] * 1
        """
        )
        binop = node.body[0].value
        inferred = next(binop.infer())
        self.assertEqual(inferred.as_string(), "[Uninferable]")
        self.assertEqual(binop.as_string(), "[arg] * 1")

    def test_frozenset_as_string(self) -> None:
        ast_nodes = builder.extract_node(
            """
        frozenset((1, 2, 3)) #@
        frozenset({1, 2, 3}) #@
        frozenset([1, 2, 3,]) #@

        frozenset(None) #@
        frozenset(1) #@
        """
        )
        ast_nodes = [next(node.infer()) for node in ast_nodes]
        assert isinstance(ast_nodes, list)
        self.assertEqual(ast_nodes[0].as_string(), "frozenset((1, 2, 3))")
        self.assertEqual(ast_nodes[1].as_string(), "frozenset({1, 2, 3})")
        self.assertEqual(ast_nodes[2].as_string(), "frozenset([1, 2, 3])")

        self.assertNotEqual(ast_nodes[3].as_string(), "frozenset(None)")
        self.assertNotEqual(ast_nodes[4].as_string(), "frozenset(1)")

    def test_varargs_kwargs_as_string(self) -> None:
        ast = abuilder.string_build("raise_string(*args, **kwargs)").body[0]
        self.assertEqual(ast.as_string(), "raise_string(*args, **kwargs)")

    def test_module_as_string(self) -> None:
        """Check as_string on a whole module prepared to be returned identically."""
        module = resources.build_file("data/module.py", "data.module")
        with open(resources.find("data/module.py"), encoding="utf-8") as fobj:
            self.assertMultiLineEqual(module.as_string(), fobj.read())

    def test_module2_as_string(self) -> None:
        """Check as_string on a whole module prepared to be returned identically."""
        module2 = resources.build_file("data/module2.py", "data.module2")
        with open(resources.find("data/module2.py"), encoding="utf-8") as fobj:
            self.assertMultiLineEqual(module2.as_string(), fobj.read())

    def test_as_string(self) -> None:
        """Check as_string for python syntax >= 2.7."""
        code = """one_two = {1, 2}
b = {v: k for (k, v) in enumerate('string')}
cdd = {k for k in b}\n\n"""
        ast = abuilder.string_build(code)
        self.assertMultiLineEqual(ast.as_string(), code)

    def test_3k_as_string(self) -> None:
        """Check as_string for python 3k syntax."""
        code = """print()

def function(var):
    nonlocal counter
    try:
        hello
    except NameError as nexc:
        (*hell, o) = b'hello'
        raise AttributeError from nexc
\n"""
        ast = abuilder.string_build(code)
        self.assertEqual(ast.as_string(), code)

    def test_3k_annotations_and_metaclass(self) -> None:
        code = '''
        def function(var: int):
            nonlocal counter

        class Language(metaclass=Natural):
            """natural language"""
        '''

        code_annotations = textwrap.dedent(code)
        expected = '''\
def function(var: int):
    nonlocal counter


class Language(metaclass=Natural):
    """natural language"""'''
        ast = abuilder.string_build(code_annotations)
        self.assertEqual(ast.as_string().strip(), expected)

    def test_ellipsis(self) -> None:
        ast = abuilder.string_build("a[...]").body[0]
        self.assertEqual(ast.as_string(), "a[...]")

    def test_slices(self) -> None:
        for code in (
            "a[0]",
            "a[1:3]",
            "a[:-1:step]",
            "a[:, newaxis]",
            "a[newaxis, :]",
            "del L[::2]",
            "del A[1]",
            "del Br[:]",
        ):
            ast = abuilder.string_build(code).body[0]
            self.assertEqual(ast.as_string(), code)

    def test_slice_and_subscripts(self) -> None:
        code = """a[:1] = bord[2:]
a[:1] = bord[2:]
del bree[3:d]
bord[2:]
del av[d::f], a[df:]
a[:1] = bord[2:]
del SRC[::1, newaxis, 1:]
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

    def test_int_attribute(self) -> None:
        code = """
x = (-3).real
y = (3).imag
        """
        ast = abuilder.string_build(code)
        self.assertEqual(ast.as_string().strip(), code.strip())

    def test_operator_precedence(self) -> None:
        with open(resources.find("data/operator_precedence.py"), encoding="utf-8") as f:
            for code in f:
                self.check_as_string_ast_equality(code)

    @staticmethod
    def check_as_string_ast_equality(code: str) -> None:
        """
        Check that as_string produces source code with exactly the same
        semantics as the source it was originally parsed from.
        """
        pre = builder.parse(code)
        post = builder.parse(pre.as_string())

        pre_repr = pre.repr_tree()
        post_repr = post.repr_tree()

        assert pre_repr == post_repr
        assert pre.as_string().strip() == code.strip()

    def test_class_def(self) -> None:
        code = """
import abc
from typing import Tuple


class A:
    pass



class B(metaclass=A, x=1):
    pass



class C(B):
    pass



class D(metaclass=abc.ABCMeta):
    pass


def func(param: Tuple):
    pass
"""
        ast = abuilder.string_build(code)
        self.assertEqual(ast.as_string().strip(), code.strip())

    def test_f_strings(self):
        code = r'''
a = f"{'a'}"
b = f'{{b}}'
c = f""" "{'c'}" """
d = f'{d!r} {d!s} {d!a}'
e = f'{e:.3}'
f = f'{f:{x}.{y}}'
n = f'\n'
everything = f""" " \' \r \t \\ {{ }} {'x' + x!r:a} {["'"]!s:{a}}"""
'''
        ast = abuilder.string_build(code)
        self.assertEqual(ast.as_string().strip(), code.strip())

    @staticmethod
    def test_as_string_unknown() -> None:
        assert nodes.Unknown().as_string() == "Unknown.Unknown()"
        assert nodes.Unknown(lineno=1, col_offset=0).as_string() == "Unknown.Unknown()"

    @staticmethod
    @pytest.mark.skipif(
        IS_PYPY,
        reason="Test requires manipulating the recursion limit, which cannot "
        "be undone in a finally block without polluting other tests on PyPy.",
    )
    def test_recursion_error_trapped() -> None:
        with pytest.warns(UserWarning, match="unable to transform"):
            ast = abuilder.string_build(LONG_CHAINED_METHOD_CALL)

        attribute = ast.body[1].value.func
        with pytest.raises(UserWarning):
            attribute.as_string()


@pytest.mark.skipif(not PY312_PLUS, reason="Uses 3.12 type param nodes")
class AsStringTypeParamNodes(unittest.TestCase):
    @staticmethod
    def test_as_string_type_alias() -> None:
        ast = abuilder.string_build("type Point = tuple[float, float]")
        type_alias = ast.body[0]
        assert type_alias.as_string().strip() == "Point"

    @staticmethod
    def test_as_string_type_var() -> None:
        ast = abuilder.string_build("type Point[T] = tuple[float, float]")
        type_var = ast.body[0].type_params[0]
        assert type_var.as_string().strip() == "T"

    @staticmethod
    def test_as_string_type_var_tuple() -> None:
        ast = abuilder.string_build("type Alias[*Ts] = tuple[*Ts]")
        type_var_tuple = ast.body[0].type_params[0]
        assert type_var_tuple.as_string().strip() == "*Ts"

    @staticmethod
    def test_as_string_param_spec() -> None:
        ast = abuilder.string_build("type Alias[**P] = Callable[P, int]")
        param_spec = ast.body[0].type_params[0]
        assert param_spec.as_string().strip() == "P"


class _NodeTest(unittest.TestCase):
    """Test transformation of If Node."""

    CODE = ""

    @property
    def astroid(self) -> Module:
        try:
            return self.__class__.__dict__["CODE_Astroid"]
        except KeyError:
            module = builder.parse(self.CODE)
            self.__class__.CODE_Astroid = module
            return module


class IfNodeTest(_NodeTest):
    """Test transformation of If Node."""

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

    def test_if_elif_else_node(self) -> None:
        """Test transformation for If node."""
        self.assertEqual(len(self.astroid.body), 4)
        for stmt in self.astroid.body:
            self.assertIsInstance(stmt, nodes.If)
        self.assertFalse(self.astroid.body[0].orelse)  # simple If
        self.assertIsInstance(self.astroid.body[1].orelse[0], nodes.Pass)  # If / else
        self.assertIsInstance(self.astroid.body[2].orelse[0], nodes.If)  # If / elif
        self.assertIsInstance(self.astroid.body[3].orelse[0].orelse[0], nodes.If)

    def test_block_range(self) -> None:
        # XXX ensure expected values
        self.assertEqual(self.astroid.block_range(1), (0, 22))
        self.assertEqual(self.astroid.block_range(10), (0, 22))  # XXX (10, 22) ?
        self.assertEqual(self.astroid.body[1].block_range(5), (5, 6))
        self.assertEqual(self.astroid.body[1].block_range(6), (6, 6))
        self.assertEqual(self.astroid.body[1].orelse[0].block_range(7), (7, 8))
        self.assertEqual(self.astroid.body[1].orelse[0].block_range(8), (8, 8))


class TryNodeTest(_NodeTest):
    CODE = """
        try:  # L2
            print("Hello")
        except IOError:
            pass
        except UnicodeError:
            pass
        else:
            print()
        finally:
            print()
    """

    def test_block_range(self) -> None:
        try_node = self.astroid.body[0]
        assert try_node.block_range(1) == (1, 11)
        assert try_node.block_range(2) == (2, 2)
        assert try_node.block_range(3) == (3, 3)
        assert try_node.block_range(4) == (4, 4)
        assert try_node.block_range(5) == (5, 5)
        assert try_node.block_range(6) == (6, 6)
        assert try_node.block_range(7) == (7, 7)
        assert try_node.block_range(8) == (8, 8)
        assert try_node.block_range(9) == (9, 9)
        assert try_node.block_range(10) == (10, 10)
        assert try_node.block_range(11) == (11, 11)


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

    def test_block_range(self) -> None:
        # XXX ensure expected values
        self.assertEqual(self.astroid.body[0].block_range(1), (1, 9))
        self.assertEqual(self.astroid.body[0].block_range(2), (2, 2))
        self.assertEqual(self.astroid.body[0].block_range(3), (3, 3))
        self.assertEqual(self.astroid.body[0].block_range(4), (4, 4))
        self.assertEqual(self.astroid.body[0].block_range(5), (5, 5))
        self.assertEqual(self.astroid.body[0].block_range(6), (6, 6))
        self.assertEqual(self.astroid.body[0].block_range(7), (7, 7))
        self.assertEqual(self.astroid.body[0].block_range(8), (8, 8))
        self.assertEqual(self.astroid.body[0].block_range(9), (9, 9))


class TryFinallyNodeTest(_NodeTest):
    CODE = """
        try:
            print ('pouet')
        finally:
            print ('pouet')
    """

    def test_block_range(self) -> None:
        # XXX ensure expected values
        self.assertEqual(self.astroid.body[0].block_range(1), (1, 5))
        self.assertEqual(self.astroid.body[0].block_range(2), (2, 2))
        self.assertEqual(self.astroid.body[0].block_range(3), (3, 3))
        self.assertEqual(self.astroid.body[0].block_range(4), (4, 4))
        self.assertEqual(self.astroid.body[0].block_range(5), (5, 5))


class TryExceptFinallyNodeTest(_NodeTest):
    CODE = """
        try:
            print('pouet')
        except Exception:
            print ('oops')
        finally:
            print ('pouet')
    """

    def test_block_range(self) -> None:
        # XXX ensure expected values
        self.assertEqual(self.astroid.body[0].block_range(1), (1, 7))
        self.assertEqual(self.astroid.body[0].block_range(2), (2, 2))
        self.assertEqual(self.astroid.body[0].block_range(3), (3, 3))
        self.assertEqual(self.astroid.body[0].block_range(4), (4, 4))
        self.assertEqual(self.astroid.body[0].block_range(5), (5, 5))
        self.assertEqual(self.astroid.body[0].block_range(6), (6, 6))
        self.assertEqual(self.astroid.body[0].block_range(7), (7, 7))


class ImportNodeTest(resources.SysPathSetup, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.module = resources.build_file("data/module.py", "data.module")
        self.module2 = resources.build_file("data/module2.py", "data.module2")

    def test_import_self_resolve(self) -> None:
        myos = next(self.module2.igetattr("myos"))
        self.assertTrue(isinstance(myos, nodes.Module), myos)
        self.assertEqual(myos.name, "os")
        self.assertEqual(myos.qname(), "os")
        self.assertEqual(myos.pytype(), "builtins.module")

    def test_from_self_resolve(self) -> None:
        namenode = next(self.module.igetattr("NameNode"))
        self.assertTrue(isinstance(namenode, nodes.ClassDef), namenode)
        self.assertEqual(namenode.root().name, "astroid.nodes.node_classes")
        self.assertEqual(namenode.qname(), "astroid.nodes.node_classes.Name")
        self.assertEqual(namenode.pytype(), "builtins.type")
        abspath = next(self.module2.igetattr("abspath"))
        self.assertTrue(isinstance(abspath, nodes.FunctionDef), abspath)
        self.assertEqual(abspath.root().name, "os.path")
        self.assertEqual(abspath.pytype(), "builtins.function")
        if sys.platform != "win32":
            # Not sure what is causing this check to fail on Windows.
            # For some reason the abspath() inference returns a different
            # path than expected:
            # AssertionError: 'os.path._abspath_fallback' != 'os.path.abspath'
            self.assertEqual(abspath.qname(), "os.path.abspath")

    def test_real_name(self) -> None:
        from_ = self.module["NameNode"]
        self.assertEqual(from_.real_name("NameNode"), "Name")
        imp_ = self.module["os"]
        self.assertEqual(imp_.real_name("os"), "os")
        self.assertRaises(AttributeInferenceError, imp_.real_name, "os.path")
        imp_ = self.module["NameNode"]
        self.assertEqual(imp_.real_name("NameNode"), "Name")
        self.assertRaises(AttributeInferenceError, imp_.real_name, "Name")
        imp_ = self.module2["YO"]
        self.assertEqual(imp_.real_name("YO"), "YO")
        self.assertRaises(AttributeInferenceError, imp_.real_name, "data")

    def test_as_string(self) -> None:
        ast = self.module["modutils"]
        self.assertEqual(ast.as_string(), "from astroid import modutils")
        ast = self.module["NameNode"]
        self.assertEqual(
            ast.as_string(), "from astroid.nodes.node_classes import Name as NameNode"
        )
        ast = self.module["os"]
        self.assertEqual(ast.as_string(), "import os.path")
        code = """from . import here
from .. import door
from .store import bread
from ..cave import wine\n\n"""
        ast = abuilder.string_build(code)
        self.assertMultiLineEqual(ast.as_string(), code)

    def test_bad_import_inference(self) -> None:
        # Explication of bug
        """When we import PickleError from nonexistent, a call to the infer
        method of this From node will be made by unpack_infer.
        inference.infer_from will try to import this module, which will fail and
        raise a InferenceException (by ImportNode.do_import_module). The infer_name
        will catch this exception and yield and Uninferable instead.
        """

        code = """
            try:
                from pickle import PickleError
            except ImportError:
                from nonexistent import PickleError

            try:
                pass
            except PickleError:
                pass
        """
        module = builder.parse(code)
        handler_type = module.body[1].handlers[0].type

        excs = list(nodes.unpack_infer(handler_type))
        # The number of returned object can differ on Python 2
        # and Python 3. In one version, an additional item will
        # be returned, from the _pickle module, which is not
        # present in the other version.
        self.assertIsInstance(excs[0], nodes.ClassDef)
        self.assertEqual(excs[0].name, "PickleError")
        self.assertIs(excs[-1], util.Uninferable)

    def test_absolute_import(self) -> None:
        module = resources.build_file("data/absimport.py")
        ctx = InferenceContext()
        # will fail if absolute import failed
        ctx.lookupname = "message"
        next(module["message"].infer(ctx))
        ctx.lookupname = "email"
        m = next(module["email"].infer(ctx))
        self.assertFalse(m.file.startswith(os.path.join("data", "email.py")))

    def test_more_absolute_import(self) -> None:
        module = resources.build_file("data/module1abs/__init__.py", "data.module1abs")
        self.assertIn("sys", module.locals)

    _pickle_names = ("dump",)  # "dumps", "load", "loads")

    def test_conditional(self) -> None:
        module = resources.build_file("data/conditional_import/__init__.py")
        ctx = InferenceContext()

        for name in self._pickle_names:
            ctx.lookupname = name
            some = list(module[name].infer(ctx))
            assert Uninferable not in some, name

    def test_conditional_import(self) -> None:
        module = resources.build_file("data/conditional.py")
        ctx = InferenceContext()

        for name in self._pickle_names:
            ctx.lookupname = name
            some = list(module[name].infer(ctx))
            assert Uninferable not in some, name


class CmpNodeTest(unittest.TestCase):
    def test_as_string(self) -> None:
        ast = abuilder.string_build("a == 2").body[0]
        self.assertEqual(ast.as_string(), "a == 2")


class ConstNodeTest(unittest.TestCase):
    def _test(self, value: Any) -> None:
        node = nodes.const_factory(value)
        self.assertIsInstance(node._proxied, nodes.ClassDef)
        self.assertEqual(node._proxied.name, value.__class__.__name__)
        self.assertIs(node.value, value)
        self.assertTrue(node._proxied.parent)
        self.assertEqual(node._proxied.root().name, value.__class__.__module__)
        with self.assertRaises(StatementMissing):
            with pytest.warns(DeprecationWarning) as records:
                node.statement(future=True)
                assert len(records) == 1
        with self.assertRaises(StatementMissing):
            node.statement()

        with self.assertRaises(ParentMissingError):
            with pytest.warns(DeprecationWarning) as records:
                node.frame(future=True)
                assert len(records) == 1
        with self.assertRaises(ParentMissingError):
            node.frame()

    def test_none(self) -> None:
        self._test(None)

    def test_bool(self) -> None:
        self._test(True)

    def test_int(self) -> None:
        self._test(1)

    def test_float(self) -> None:
        self._test(1.0)

    def test_complex(self) -> None:
        self._test(1.0j)

    def test_str(self) -> None:
        self._test("a")

    def test_unicode(self) -> None:
        self._test("a")

    def test_str_kind(self):
        node = builder.extract_node(
            """
            const = u"foo"
        """
        )
        assert isinstance(node.value, nodes.Const)
        assert node.value.value == "foo"
        assert node.value.kind, "u"

    def test_copy(self) -> None:
        """Make sure copying a Const object doesn't result in infinite recursion."""
        const = copy.copy(nodes.Const(1))
        assert const.value == 1


class NameNodeTest(unittest.TestCase):
    def test_assign_to_true(self) -> None:
        """Test that True and False assignments don't crash."""
        code = """
            True = False
            def hello(False):
                pass
            del True
        """
        with self.assertRaises(AstroidBuildingError):
            builder.parse(code)


class TestNamedExprNode:
    """Tests for the NamedExpr node."""

    @staticmethod
    def test_frame() -> None:
        """Test if the frame of NamedExpr is correctly set for certain types
        of parent nodes.
        """
        module = builder.parse(
            """
            def func(var_1):
                pass

            def func_two(var_2, var_2 = (named_expr_1 := "walrus")):
                pass

            class MyBaseClass:
                pass

            class MyInheritedClass(MyBaseClass, var_3=(named_expr_2 := "walrus")):
                pass

            VAR = lambda y = (named_expr_3 := "walrus"): print(y)

            def func_with_lambda(
                var_5 = (
                    named_expr_4 := lambda y = (named_expr_5 := "walrus"): y
                    )
                ):
                pass

            COMPREHENSION = [y for i in (1, 2) if (y := i ** 2)]
        """
        )
        function = module.body[0]
        assert function.args.frame() == function
        assert function.args.frame() == function

        function_two = module.body[1]
        assert function_two.args.args[0].frame() == function_two
        assert function_two.args.args[0].frame() == function_two
        assert function_two.args.args[1].frame() == function_two
        assert function_two.args.args[1].frame() == function_two
        assert function_two.args.defaults[0].frame() == module
        assert function_two.args.defaults[0].frame() == module

        inherited_class = module.body[3]
        assert inherited_class.keywords[0].frame() == inherited_class
        assert inherited_class.keywords[0].frame() == inherited_class
        assert inherited_class.keywords[0].value.frame() == module
        assert inherited_class.keywords[0].value.frame() == module

        lambda_assignment = module.body[4].value
        assert lambda_assignment.args.args[0].frame() == lambda_assignment
        assert lambda_assignment.args.args[0].frame() == lambda_assignment
        assert lambda_assignment.args.defaults[0].frame() == module
        assert lambda_assignment.args.defaults[0].frame() == module

        lambda_named_expr = module.body[5].args.defaults[0]
        assert lambda_named_expr.value.args.defaults[0].frame() == module
        assert lambda_named_expr.value.args.defaults[0].frame() == module

        comprehension = module.body[6].value
        assert comprehension.generators[0].ifs[0].frame() == module
        assert comprehension.generators[0].ifs[0].frame() == module

    @staticmethod
    def test_scope() -> None:
        """Test if the scope of NamedExpr is correctly set for certain types
        of parent nodes.
        """
        module = builder.parse(
            """
            def func(var_1):
                pass

            def func_two(var_2, var_2 = (named_expr_1 := "walrus")):
                pass

            class MyBaseClass:
                pass

            class MyInheritedClass(MyBaseClass, var_3=(named_expr_2 := "walrus")):
                pass

            VAR = lambda y = (named_expr_3 := "walrus"): print(y)

            def func_with_lambda(
                var_5 = (
                    named_expr_4 := lambda y = (named_expr_5 := "walrus"): y
                    )
                ):
                pass

            COMPREHENSION = [y for i in (1, 2) if (y := i ** 2)]
        """
        )
        function = module.body[0]
        assert function.args.scope() == function

        function_two = module.body[1]
        assert function_two.args.args[0].scope() == function_two
        assert function_two.args.args[1].scope() == function_two
        assert function_two.args.defaults[0].scope() == module

        inherited_class = module.body[3]
        assert inherited_class.keywords[0].scope() == inherited_class
        assert inherited_class.keywords[0].value.scope() == module

        lambda_assignment = module.body[4].value
        assert lambda_assignment.args.args[0].scope() == lambda_assignment
        assert lambda_assignment.args.defaults[0].scope()

        lambda_named_expr = module.body[5].args.defaults[0]
        assert lambda_named_expr.value.args.defaults[0].scope() == module

        comprehension = module.body[6].value
        assert comprehension.generators[0].ifs[0].scope() == module


class AnnAssignNodeTest(unittest.TestCase):
    def test_primitive(self) -> None:
        code = textwrap.dedent(
            """
            test: int = 5
        """
        )
        assign = builder.extract_node(code)
        self.assertIsInstance(assign, nodes.AnnAssign)
        self.assertEqual(assign.target.name, "test")
        self.assertEqual(assign.annotation.name, "int")
        self.assertEqual(assign.value.value, 5)
        self.assertEqual(assign.simple, 1)

    def test_primitive_without_initial_value(self) -> None:
        code = textwrap.dedent(
            """
            test: str
        """
        )
        assign = builder.extract_node(code)
        self.assertIsInstance(assign, nodes.AnnAssign)
        self.assertEqual(assign.target.name, "test")
        self.assertEqual(assign.annotation.name, "str")
        self.assertEqual(assign.value, None)

    def test_complex(self) -> None:
        code = textwrap.dedent(
            """
            test: Dict[List[str]] = {}
        """
        )
        assign = builder.extract_node(code)
        self.assertIsInstance(assign, nodes.AnnAssign)
        self.assertEqual(assign.target.name, "test")
        self.assertIsInstance(assign.annotation, astroid.Subscript)
        self.assertIsInstance(assign.value, astroid.Dict)

    def test_as_string(self) -> None:
        code = textwrap.dedent(
            """
            print()
            test: int = 5
            test2: str
            test3: List[Dict[str, str]] = []
        """
        )
        ast = abuilder.string_build(code)
        self.assertEqual(ast.as_string().strip(), code.strip())


class ArgumentsNodeTC(unittest.TestCase):
    def test_linenumbering(self) -> None:
        ast = builder.parse(
            """
            def func(a,
                b): pass
            x = lambda x: None
        """
        )
        self.assertEqual(ast["func"].args.fromlineno, 2)
        self.assertFalse(ast["func"].args.is_statement)
        xlambda = next(ast["x"].infer())
        self.assertEqual(xlambda.args.fromlineno, 4)
        self.assertEqual(xlambda.args.tolineno, 4)
        self.assertFalse(xlambda.args.is_statement)

    def test_kwoargs(self) -> None:
        ast = builder.parse(
            """
            def func(*, x):
                pass
        """
        )
        args = ast["func"].args
        assert isinstance(args, nodes.Arguments)
        assert args.is_argument("x")
        assert args.kw_defaults == [None]

        ast = builder.parse(
            """
            def func(*, x = "default"):
                pass
        """
        )
        args = ast["func"].args
        assert isinstance(args, nodes.Arguments)
        assert args.is_argument("x")
        assert len(args.kw_defaults) == 1
        assert isinstance(args.kw_defaults[0], nodes.Const)
        assert args.kw_defaults[0].value == "default"

    def test_positional_only(self):
        ast = builder.parse(
            """
            def func(x, /, y):
                pass
        """
        )
        args = ast["func"].args
        self.assertTrue(args.is_argument("x"))
        self.assertTrue(args.is_argument("y"))
        index, node = args.find_argname("x")
        self.assertEqual(index, 0)
        self.assertIsNotNone(node)


class UnboundMethodNodeTest(unittest.TestCase):
    def test_no_super_getattr(self) -> None:
        # This is a test for issue
        # https://bitbucket.org/logilab/astroid/issue/91, which tests
        # that UnboundMethod doesn't call super when doing .getattr.

        ast = builder.parse(
            """
        class A(object):
            def test(self):
                pass
        meth = A.test
        """
        )
        node = next(ast["meth"].infer())
        with self.assertRaises(AttributeInferenceError):
            node.getattr("__missssing__")
        name = node.getattr("__name__")[0]
        self.assertIsInstance(name, nodes.Const)
        self.assertEqual(name.value, "test")


class BoundMethodNodeTest(unittest.TestCase):
    def test_is_property(self) -> None:
        ast = builder.parse(
            """
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
        """
        )
        for prop in (
            "builtin_property",
            "abc_property",
            "cached_p",
            "reified",
            "lazy_prop",
            "lazyprop",
            "decorated_with_lazy",
        ):
            inferred = next(ast[prop].infer())
            self.assertIsInstance(inferred, nodes.Const, prop)
            self.assertEqual(inferred.value, 42, prop)

        inferred = next(ast["not_prop"].infer())
        self.assertIsInstance(inferred, bases.BoundMethod)


class AliasesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.transformer = transforms.TransformVisitor()

    def parse_transform(self, code: str) -> Module:
        module = parse(code, apply_transforms=False)
        return self.transformer.visit(module)

    def test_aliases(self) -> None:
        def test_from(node: ImportFrom) -> ImportFrom:
            node.names = [*node.names, ("absolute_import", None)]
            return node

        def test_class(node: ClassDef) -> ClassDef:
            node.name = "Bar"
            return node

        def test_function(node: FunctionDef) -> FunctionDef:
            node.name = "another_test"
            return node

        def test_callfunc(node: Call) -> Call | None:
            if node.func.name == "Foo":
                node.func.name = "Bar"
                return node
            return None

        def test_assname(node: AssignName) -> AssignName | None:
            if node.name == "foo":
                return nodes.AssignName(
                    "bar",
                    node.lineno,
                    node.col_offset,
                    node.parent,
                    end_lineno=node.end_lineno,
                    end_col_offset=node.end_col_offset,
                )
            return None

        def test_assattr(node: AssignAttr) -> AssignAttr:
            if node.attrname == "a":
                node.attrname = "b"
                return node
            return None

        def test_getattr(node: Attribute) -> Attribute:
            if node.attrname == "a":
                node.attrname = "b"
                return node
            return None

        def test_genexpr(node: GeneratorExp) -> GeneratorExp:
            if node.elt.value == 1:
                node.elt = nodes.Const(2, node.lineno, node.col_offset, node.parent)
                return node
            return None

        self.transformer.register_transform(nodes.ImportFrom, test_from)
        self.transformer.register_transform(nodes.ClassDef, test_class)
        self.transformer.register_transform(nodes.FunctionDef, test_function)
        self.transformer.register_transform(nodes.Call, test_callfunc)
        self.transformer.register_transform(nodes.AssignName, test_assname)
        self.transformer.register_transform(nodes.AssignAttr, test_assattr)
        self.transformer.register_transform(nodes.Attribute, test_getattr)
        self.transformer.register_transform(nodes.GeneratorExp, test_genexpr)

        string = """
        from __future__ import print_function

        class Foo: pass

        def test(a): return a

        foo = Foo()
        foo.a = test(42)
        foo.a
        (1 for _ in range(0, 42))
        """

        module = self.parse_transform(string)

        self.assertEqual(len(module.body[0].names), 2)
        self.assertIsInstance(module.body[0], nodes.ImportFrom)
        self.assertEqual(module.body[1].name, "Bar")
        self.assertIsInstance(module.body[1], nodes.ClassDef)
        self.assertEqual(module.body[2].name, "another_test")
        self.assertIsInstance(module.body[2], nodes.FunctionDef)
        self.assertEqual(module.body[3].targets[0].name, "bar")
        self.assertIsInstance(module.body[3].targets[0], nodes.AssignName)
        self.assertEqual(module.body[3].value.func.name, "Bar")
        self.assertIsInstance(module.body[3].value, nodes.Call)
        self.assertEqual(module.body[4].targets[0].attrname, "b")
        self.assertIsInstance(module.body[4].targets[0], nodes.AssignAttr)
        self.assertIsInstance(module.body[5], nodes.Expr)
        self.assertEqual(module.body[5].value.attrname, "b")
        self.assertIsInstance(module.body[5].value, nodes.Attribute)
        self.assertEqual(module.body[6].value.elt.value, 2)
        self.assertIsInstance(module.body[6].value, nodes.GeneratorExp)


class Python35AsyncTest(unittest.TestCase):
    def test_async_await_keywords(self) -> None:
        (
            async_def,
            async_for,
            async_with,
            async_for2,
            async_with2,
            await_node,
        ) = builder.extract_node(
            """
        async def func(): #@
            async for i in range(10): #@
                f = __(await i)
            async with test(): #@
                pass
            async for i \
                    in range(10):  #@
                pass
            async with test(), \
                    test2():  #@
                pass
        """
        )
        assert isinstance(async_def, nodes.AsyncFunctionDef)
        assert async_def.lineno == 2
        assert async_def.col_offset == 0

        assert isinstance(async_for, nodes.AsyncFor)
        assert async_for.lineno == 3
        assert async_for.col_offset == 4

        assert isinstance(async_with, nodes.AsyncWith)
        assert async_with.lineno == 5
        assert async_with.col_offset == 4

        assert isinstance(async_for2, nodes.AsyncFor)
        assert async_for2.lineno == 7
        assert async_for2.col_offset == 4

        assert isinstance(async_with2, nodes.AsyncWith)
        assert async_with2.lineno == 9
        assert async_with2.col_offset == 4

        assert isinstance(await_node, nodes.Await)
        assert isinstance(await_node.value, nodes.Name)
        assert await_node.lineno == 4
        assert await_node.col_offset == 15

    def _test_await_async_as_string(self, code: str) -> None:
        ast_node = parse(code)
        self.assertEqual(ast_node.as_string().strip(), code.strip())

    def test_await_as_string(self) -> None:
        code = textwrap.dedent(
            """
        async def function():
            await 42
            await x[0]
            (await x)[0]
            await (x + y)[0]
        """
        )
        self._test_await_async_as_string(code)

    def test_asyncwith_as_string(self) -> None:
        code = textwrap.dedent(
            """
        async def function():
            async with 42:
                pass
        """
        )
        self._test_await_async_as_string(code)

    def test_asyncfor_as_string(self) -> None:
        code = textwrap.dedent(
            """
        async def function():
            async for i in range(10):
                await 42
        """
        )
        self._test_await_async_as_string(code)

    def test_decorated_async_def_as_string(self) -> None:
        code = textwrap.dedent(
            """
        @decorator
        async def function():
            async for i in range(10):
                await 42
        """
        )
        self._test_await_async_as_string(code)


class ContextTest(unittest.TestCase):
    def test_subscript_load(self) -> None:
        node = builder.extract_node("f[1]")
        self.assertIs(node.ctx, Context.Load)

    def test_subscript_del(self) -> None:
        node = builder.extract_node("del f[1]")
        self.assertIs(node.targets[0].ctx, Context.Del)

    def test_subscript_store(self) -> None:
        node = builder.extract_node("f[1] = 2")
        subscript = node.targets[0]
        self.assertIs(subscript.ctx, Context.Store)

    def test_list_load(self) -> None:
        node = builder.extract_node("[]")
        self.assertIs(node.ctx, Context.Load)

    def test_list_del(self) -> None:
        node = builder.extract_node("del []")
        self.assertIs(node.targets[0].ctx, Context.Del)

    def test_list_store(self) -> None:
        with self.assertRaises(AstroidSyntaxError):
            builder.extract_node("[0] = 2")

    def test_tuple_load(self) -> None:
        node = builder.extract_node("(1, )")
        self.assertIs(node.ctx, Context.Load)

    def test_tuple_store(self) -> None:
        with self.assertRaises(AstroidSyntaxError):
            builder.extract_node("(1, ) = 3")

    def test_starred_load(self) -> None:
        node = builder.extract_node("a = *b")
        starred = node.value
        self.assertIs(starred.ctx, Context.Load)

    def test_starred_store(self) -> None:
        node = builder.extract_node("a, *b = 1, 2")
        starred = node.targets[0].elts[1]
        self.assertIs(starred.ctx, Context.Store)


def test_unknown() -> None:
    """Test Unknown node."""
    assert isinstance(next(nodes.Unknown().infer()), type(util.Uninferable))
    assert isinstance(nodes.Unknown().name, str)
    assert isinstance(nodes.Unknown().qname(), str)


def test_type_comments_with() -> None:
    module = builder.parse(
        """
    with a as b: # type: int
        pass
    with a as b: # type: ignore[name-defined]
        pass
    """
    )
    node = module.body[0]
    ignored_node = module.body[1]
    assert isinstance(node.type_annotation, astroid.Name)

    assert ignored_node.type_annotation is None


def test_type_comments_for() -> None:
    module = builder.parse(
        """
    for a, b in [1, 2, 3]: # type: List[int]
        pass
    for a, b in [1, 2, 3]: # type: ignore[name-defined]
        pass
    """
    )
    node = module.body[0]
    ignored_node = module.body[1]
    assert isinstance(node.type_annotation, astroid.Subscript)
    assert node.type_annotation.as_string() == "List[int]"

    assert ignored_node.type_annotation is None


def test_type_coments_assign() -> None:
    module = builder.parse(
        """
    a, b = [1, 2, 3] # type: List[int]
    a, b = [1, 2, 3] # type: ignore[name-defined]
    """
    )
    node = module.body[0]
    ignored_node = module.body[1]
    assert isinstance(node.type_annotation, astroid.Subscript)
    assert node.type_annotation.as_string() == "List[int]"

    assert ignored_node.type_annotation is None


def test_type_comments_invalid_expression() -> None:
    module = builder.parse(
        """
    a, b = [1, 2, 3] # type: something completely invalid
    a, b = [1, 2, 3] # typeee: 2*+4
    a, b = [1, 2, 3] # type: List[int
    """
    )
    for node in module.body:
        assert node.type_annotation is None


def test_type_comments_invalid_function_comments() -> None:
    module = builder.parse(
        """
    def func(
        # type: () -> int # inside parentheses
    ):
        pass
    def func():
        # type: something completely invalid
        pass
    def func1():
        # typeee: 2*+4
        pass
    def func2():
        # type: List[int
        pass
    """
    )
    for node in module.body:
        assert node.type_comment_returns is None
        assert node.type_comment_args is None


def test_type_comments_function() -> None:
    module = builder.parse(
        """
    def func():
        # type: (int) -> str
        pass
    def func1():
        # type: (int, int, int) -> (str, str)
        pass
    def func2():
        # type: (int, int, str, List[int]) -> List[int]
        pass
    """
    )
    expected_annotations = [
        (["int"], astroid.Name, "str"),
        (["int", "int", "int"], astroid.Tuple, "(str, str)"),
        (["int", "int", "str", "List[int]"], astroid.Subscript, "List[int]"),
    ]
    for node, (expected_args, expected_returns_type, expected_returns_string) in zip(
        module.body, expected_annotations
    ):
        assert node.type_comment_returns is not None
        assert node.type_comment_args is not None
        for expected_arg, actual_arg in zip(expected_args, node.type_comment_args):
            assert actual_arg.as_string() == expected_arg
        assert isinstance(node.type_comment_returns, expected_returns_type)
        assert node.type_comment_returns.as_string() == expected_returns_string


def test_type_comments_arguments() -> None:
    module = builder.parse(
        """
    def func(
        a,  # type: int
    ):
        # type: (...) -> str
        pass
    def func1(
        a,  # type: int
        b,  # type: int
        c,  # type: int
    ):
        # type: (...) -> (str, str)
        pass
    def func2(
        a,  # type: int
        b,  # type: int
        c,  # type: str
        d,  # type: List[int]
    ):
        # type: (...) -> List[int]
        pass
    """
    )
    expected_annotations = [
        ["int"],
        ["int", "int", "int"],
        ["int", "int", "str", "List[int]"],
    ]
    for node, expected_args in zip(module.body, expected_annotations):
        assert len(node.type_comment_args) == 1
        assert isinstance(node.type_comment_args[0], astroid.Const)
        assert node.type_comment_args[0].value == Ellipsis
        assert len(node.args.type_comment_args) == len(expected_args)
        for expected_arg, actual_arg in zip(expected_args, node.args.type_comment_args):
            assert actual_arg.as_string() == expected_arg


def test_type_comments_posonly_arguments() -> None:
    module = builder.parse(
        """
    def f_arg_comment(
        a,  # type: int
        b,  # type: int
        /,
        c,  # type: Optional[int]
        d,  # type: Optional[int]
        *,
        e,  # type: float
        f,  # type: float
    ):
        # type: (...) -> None
        pass
    """
    )
    expected_annotations = [
        [["int", "int"], ["Optional[int]", "Optional[int]"], ["float", "float"]]
    ]
    for node, expected_types in zip(module.body, expected_annotations):
        assert len(node.type_comment_args) == 1
        assert isinstance(node.type_comment_args[0], astroid.Const)
        assert node.type_comment_args[0].value == Ellipsis
        type_comments = [
            node.args.type_comment_posonlyargs,
            node.args.type_comment_args,
            node.args.type_comment_kwonlyargs,
        ]
        for expected_args, actual_args in zip(expected_types, type_comments):
            assert len(expected_args) == len(actual_args)
            for expected_arg, actual_arg in zip(expected_args, actual_args):
                assert actual_arg.as_string() == expected_arg


def test_correct_function_type_comment_parent() -> None:
    data = """
        def f(a):
            # type: (A) -> A
            pass
    """
    parsed_data = builder.parse(data)
    f = parsed_data.body[0]
    assert f.type_comment_args[0].parent is f
    assert f.type_comment_returns.parent is f


def test_is_generator_for_yield_assignments() -> None:
    node = astroid.extract_node(
        """
    class A:
        def test(self):
            a = yield
            while True:
                print(a)
                yield a
    a = A()
    a.test
    """
    )
    inferred = next(node.infer())
    assert isinstance(inferred, astroid.BoundMethod)
    assert bool(inferred.is_generator())


class AsyncGeneratorTest:
    def test_async_generator(self):
        node = astroid.extract_node(
            """
        async def a_iter(n):
            for i in range(1, n + 1):
                yield i
                await asyncio.sleep(1)
        a_iter(2) #@
        """
        )
        inferred = next(node.infer())
        assert isinstance(inferred, bases.AsyncGenerator)
        assert inferred.getattr("__aiter__")
        assert inferred.getattr("__anext__")
        assert inferred.pytype() == "builtins.async_generator"
        assert inferred.display_type() == "AsyncGenerator"

    def test_async_generator_is_generator_on_older_python(self):
        node = astroid.extract_node(
            """
        async def a_iter(n):
            for i in range(1, n + 1):
                yield i
                await asyncio.sleep(1)
        a_iter(2) #@
        """
        )
        inferred = next(node.infer())
        assert isinstance(inferred, bases.Generator)
        assert inferred.getattr("__iter__")
        assert inferred.getattr("__next__")
        assert inferred.pytype() == "builtins.generator"
        assert inferred.display_type() == "Generator"


def test_f_string_correct_line_numbering() -> None:
    """Test that we generate correct line numbers for f-strings."""
    node = astroid.extract_node(
        """
    def func_foo(arg_bar, arg_foo):
        dict_foo = {}

        f'{arg_bar.attr_bar}' #@
    """
    )
    assert node.lineno == 5
    assert node.last_child().lineno == 5
    assert node.last_child().last_child().lineno == 5


def test_assignment_expression() -> None:
    code = """
    if __(a := 1):
        pass
    if __(b := test):
        pass
    """
    first, second = astroid.extract_node(code)

    assert isinstance(first.target, nodes.AssignName)
    assert first.target.name == "a"
    assert isinstance(first.value, nodes.Const)
    assert first.value.value == 1
    assert first.as_string() == "a := 1"

    assert isinstance(second.target, nodes.AssignName)
    assert second.target.name == "b"
    assert isinstance(second.value, nodes.Name)
    assert second.value.name == "test"
    assert second.as_string() == "b := test"


def test_assignment_expression_in_functiondef() -> None:
    code = """
    def function(param = (assignment := "walrus")):
        def inner_function(inner_param = (inner_assign := "walrus")):
            pass
        pass

    class MyClass(attr = (assignment_two := "walrus")):
        pass

    VAR = lambda y = (assignment_three := "walrus"): print(y)

    def func_with_lambda(
        param=(named_expr_four := lambda y=(assignment_four := "walrus"): y),
    ):
        pass

    COMPREHENSION = [y for i in (1, 2) if (assignment_five := i ** 2)]

    def func():
        var = lambda y = (assignment_six := 2): print(y)

    VAR_TWO = [
        func(assignment_seven := 2)
        for _ in (1,)
    ]

    LAMBDA = lambda x: print(assignment_eight := x ** 2)

    class SomeClass:
        (assignment_nine := 2**2)
    """
    module = astroid.parse(code)

    assert "assignment" in module.locals
    assert isinstance(module.locals.get("assignment")[0], nodes.AssignName)
    function = module.body[0]
    assert "inner_assign" in function.locals
    assert "inner_assign" not in module.locals
    assert isinstance(function.locals.get("inner_assign")[0], nodes.AssignName)

    assert "assignment_two" in module.locals
    assert isinstance(module.locals.get("assignment_two")[0], nodes.AssignName)

    assert "assignment_three" in module.locals
    assert isinstance(module.locals.get("assignment_three")[0], nodes.AssignName)

    assert "assignment_four" in module.locals
    assert isinstance(module.locals.get("assignment_four")[0], nodes.AssignName)

    assert "assignment_five" in module.locals
    assert isinstance(module.locals.get("assignment_five")[0], nodes.AssignName)

    func = module.body[5]
    assert "assignment_six" in func.locals
    assert "assignment_six" not in module.locals
    assert isinstance(func.locals.get("assignment_six")[0], nodes.AssignName)

    assert "assignment_seven" in module.locals
    assert isinstance(module.locals.get("assignment_seven")[0], nodes.AssignName)

    lambda_assign = module.body[7]
    assert "assignment_eight" in lambda_assign.value.locals
    assert "assignment_eight" not in module.locals
    assert isinstance(
        lambda_assign.value.locals.get("assignment_eight")[0], nodes.AssignName
    )

    class_assign = module.body[8]
    assert "assignment_nine" in class_assign.locals
    assert "assignment_nine" not in module.locals
    assert isinstance(class_assign.locals.get("assignment_nine")[0], nodes.AssignName)


def test_get_doc() -> None:
    code = textwrap.dedent(
        """\
    def func():
        "Docstring"
        return 1
    """
    )
    node: nodes.FunctionDef = astroid.extract_node(code)  # type: ignore[assignment]
    assert isinstance(node.doc_node, nodes.Const)
    assert node.doc_node.value == "Docstring"
    assert node.doc_node.lineno == 2
    assert node.doc_node.col_offset == 4
    assert node.doc_node.end_lineno == 2
    assert node.doc_node.end_col_offset == 15

    code = textwrap.dedent(
        """\
    def func():
        ...
        return 1
    """
    )
    node = astroid.extract_node(code)
    assert node.doc_node is None


def test_parse_fstring_debug_mode() -> None:
    node = astroid.extract_node('f"{3=}"')
    assert isinstance(node, nodes.JoinedStr)
    assert node.as_string() == "f'3={3!r}'"


def test_parse_type_comments_with_proper_parent() -> None:
    code = """
    class D: #@
        @staticmethod
        def g(
                x  # type: np.array
        ):
            pass
    """
    node = astroid.extract_node(code)
    func = node.getattr("g")[0]
    type_comments = func.args.type_comment_args
    assert len(type_comments) == 1

    type_comment = type_comments[0]
    assert isinstance(type_comment, astroid.Attribute)
    assert isinstance(type_comment.parent, astroid.Expr)
    assert isinstance(type_comment.parent.parent, astroid.Arguments)


def test_const_itered() -> None:
    code = 'a = "string"'
    node = astroid.extract_node(code).value
    assert isinstance(node, astroid.Const)
    itered = node.itered()
    assert len(itered) == 6
    assert [elem.value for elem in itered] == list("string")


def test_is_generator_for_yield_in_while() -> None:
    code = """
    def paused_iter(iterable):
        while True:
            # Continue to yield the same item until `next(i)` or `i.send(False)`
            while (yield value):
                pass
    """
    node = astroid.extract_node(code)
    assert bool(node.is_generator())


def test_is_generator_for_yield_in_if() -> None:
    code = """
    import asyncio

    def paused_iter(iterable):
        if (yield from asyncio.sleep(0.01)):
            pass
            return
    """
    node = astroid.extract_node(code)
    assert bool(node.is_generator())


def test_is_generator_for_yield_in_aug_assign() -> None:
    code = """
    def test():
        buf = ''
        while True:
            buf += yield
    """
    node = astroid.extract_node(code)
    assert bool(node.is_generator())


@pytest.mark.skipif(not PY310_PLUS, reason="pattern matching was added in PY310")
class TestPatternMatching:
    @staticmethod
    def test_match_simple():
        code = textwrap.dedent(
            """
        match status:
            case 200:
                pass
            case 401 | 402 | 403:
                pass
            case None:
                pass
            case _:
                pass
        """
        ).strip()
        node = builder.extract_node(code)
        assert node.as_string() == code
        assert isinstance(node, nodes.Match)
        assert isinstance(node.subject, nodes.Name)
        assert node.subject.name == "status"
        assert isinstance(node.cases, list) and len(node.cases) == 4
        case0, case1, case2, case3 = node.cases
        assert list(node.get_children()) == [node.subject, *node.cases]

        assert isinstance(case0.pattern, nodes.MatchValue)
        assert (
            isinstance(case0.pattern.value, astroid.Const)
            and case0.pattern.value.value == 200
        )
        assert list(case0.pattern.get_children()) == [case0.pattern.value]
        assert case0.guard is None
        assert isinstance(case0.body[0], astroid.Pass)
        assert list(case0.get_children()) == [case0.pattern, case0.body[0]]

        assert isinstance(case1.pattern, nodes.MatchOr)
        assert (
            isinstance(case1.pattern.patterns, list)
            and len(case1.pattern.patterns) == 3
        )
        for i in range(3):
            match_value = case1.pattern.patterns[i]
            assert isinstance(match_value, nodes.MatchValue)
            assert isinstance(match_value.value, nodes.Const)
            assert match_value.value.value == (401, 402, 403)[i]
        assert list(case1.pattern.get_children()) == case1.pattern.patterns

        assert isinstance(case2.pattern, nodes.MatchSingleton)
        assert case2.pattern.value is None
        assert not list(case2.pattern.get_children())

        assert isinstance(case3.pattern, nodes.MatchAs)
        assert case3.pattern.name is None
        assert case3.pattern.pattern is None
        assert not list(case3.pattern.get_children())

    @staticmethod
    def test_match_sequence():
        code = textwrap.dedent(
            """
        match status:
            case [x, 2, _, *rest] as y if x > 2:
                pass
        """
        ).strip()
        node = builder.extract_node(code)
        assert node.as_string() == code
        assert isinstance(node, nodes.Match)
        assert isinstance(node.cases, list) and len(node.cases) == 1
        case = node.cases[0]

        assert isinstance(case.pattern, nodes.MatchAs)
        assert isinstance(case.pattern.name, nodes.AssignName)
        assert case.pattern.name.name == "y"
        assert list(case.pattern.get_children()) == [
            case.pattern.pattern,
            case.pattern.name,
        ]
        assert isinstance(case.guard, nodes.Compare)
        assert isinstance(case.body[0], nodes.Pass)
        assert list(case.get_children()) == [case.pattern, case.guard, case.body[0]]

        pattern_seq = case.pattern.pattern
        assert isinstance(pattern_seq, nodes.MatchSequence)
        assert isinstance(pattern_seq.patterns, list) and len(pattern_seq.patterns) == 4
        assert (
            isinstance(pattern_seq.patterns[0], nodes.MatchAs)
            and isinstance(pattern_seq.patterns[0].name, nodes.AssignName)
            and pattern_seq.patterns[0].name.name == "x"
            and pattern_seq.patterns[0].pattern is None
        )
        assert (
            isinstance(pattern_seq.patterns[1], nodes.MatchValue)
            and isinstance(pattern_seq.patterns[1].value, nodes.Const)
            and pattern_seq.patterns[1].value.value == 2
        )
        assert (
            isinstance(pattern_seq.patterns[2], nodes.MatchAs)
            and pattern_seq.patterns[2].name is None
        )
        assert (
            isinstance(pattern_seq.patterns[3], nodes.MatchStar)
            and isinstance(pattern_seq.patterns[3].name, nodes.AssignName)
            and pattern_seq.patterns[3].name.name == "rest"
        )
        assert list(pattern_seq.patterns[3].get_children()) == [
            pattern_seq.patterns[3].name
        ]
        assert list(pattern_seq.get_children()) == pattern_seq.patterns

    @staticmethod
    def test_match_mapping():
        code = textwrap.dedent(
            """
        match status:
            case {0: x, 1: _}:
                pass
            case {**rest}:
                pass
        """
        ).strip()
        node = builder.extract_node(code)
        assert node.as_string() == code
        assert isinstance(node, nodes.Match)
        assert isinstance(node.cases, list) and len(node.cases) == 2
        case0, case1 = node.cases

        assert isinstance(case0.pattern, nodes.MatchMapping)
        assert case0.pattern.rest is None
        assert isinstance(case0.pattern.keys, list) and len(case0.pattern.keys) == 2
        assert (
            isinstance(case0.pattern.patterns, list)
            and len(case0.pattern.patterns) == 2
        )
        for i in range(2):
            key = case0.pattern.keys[i]
            assert isinstance(key, nodes.Const)
            assert key.value == i
            pattern = case0.pattern.patterns[i]
            assert isinstance(pattern, nodes.MatchAs)
            if i == 0:
                assert isinstance(pattern.name, nodes.AssignName)
                assert pattern.name.name == "x"
            elif i == 1:
                assert pattern.name is None
        assert list(case0.pattern.get_children()) == [
            *case0.pattern.keys,
            *case0.pattern.patterns,
        ]

        assert isinstance(case1.pattern, nodes.MatchMapping)
        assert isinstance(case1.pattern.rest, nodes.AssignName)
        assert case1.pattern.rest.name == "rest"
        assert isinstance(case1.pattern.keys, list) and len(case1.pattern.keys) == 0
        assert (
            isinstance(case1.pattern.patterns, list)
            and len(case1.pattern.patterns) == 0
        )
        assert list(case1.pattern.get_children()) == [case1.pattern.rest]

    @staticmethod
    def test_match_class():
        code = textwrap.dedent(
            """
        match x:
            case Point2D(0, a):
                pass
            case Point3D(x=0, y=1, z=b):
                pass
        """
        ).strip()
        node = builder.extract_node(code)
        assert node.as_string() == code
        assert isinstance(node, nodes.Match)
        assert isinstance(node.cases, list) and len(node.cases) == 2
        case0, case1 = node.cases

        assert isinstance(case0.pattern, nodes.MatchClass)
        assert isinstance(case0.pattern.cls, nodes.Name)
        assert case0.pattern.cls.name == "Point2D"
        assert (
            isinstance(case0.pattern.patterns, list)
            and len(case0.pattern.patterns) == 2
        )
        match_value = case0.pattern.patterns[0]
        assert (
            isinstance(match_value, nodes.MatchValue)
            and isinstance(match_value.value, nodes.Const)
            and match_value.value.value == 0
        )
        match_as = case0.pattern.patterns[1]
        assert (
            isinstance(match_as, nodes.MatchAs)
            and match_as.pattern is None
            and isinstance(match_as.name, nodes.AssignName)
            and match_as.name.name == "a"
        )
        assert list(case0.pattern.get_children()) == [
            case0.pattern.cls,
            *case0.pattern.patterns,
        ]

        assert isinstance(case1.pattern, nodes.MatchClass)
        assert isinstance(case1.pattern.cls, nodes.Name)
        assert case1.pattern.cls.name == "Point3D"
        assert (
            isinstance(case1.pattern.patterns, list)
            and len(case1.pattern.patterns) == 0
        )
        assert (
            isinstance(case1.pattern.kwd_attrs, list)
            and len(case1.pattern.kwd_attrs) == 3
        )
        assert (
            isinstance(case1.pattern.kwd_patterns, list)
            and len(case1.pattern.kwd_patterns) == 3
        )
        for i in range(2):
            assert case1.pattern.kwd_attrs[i] == ("x", "y")[i]
            kwd_pattern = case1.pattern.kwd_patterns[i]
            assert isinstance(kwd_pattern, nodes.MatchValue)
            assert isinstance(kwd_pattern.value, nodes.Const)
            assert kwd_pattern.value.value == i
        assert case1.pattern.kwd_attrs[2] == "z"
        kwd_pattern = case1.pattern.kwd_patterns[2]
        assert (
            isinstance(kwd_pattern, nodes.MatchAs)
            and kwd_pattern.pattern is None
            and isinstance(kwd_pattern.name, nodes.AssignName)
            and kwd_pattern.name.name == "b"
        )
        assert list(case1.pattern.get_children()) == [
            case1.pattern.cls,
            *case1.pattern.kwd_patterns,
        ]

    @staticmethod
    def test_return_from_match():
        code = textwrap.dedent(
            """
        def return_from_match(x):
            match x:
                case 10:
                    return 10
                case _:
                    return -1

        return_from_match(10)  #@
        """
        ).strip()
        node = builder.extract_node(code)
        inferred = node.inferred()
        assert len(inferred) == 2
        assert [inf.value for inf in inferred] == [10, -1]


@pytest.mark.parametrize(
    "node",
    [
        node
        for node in astroid.nodes.ALL_NODE_CLASSES
        if node.__name__ not in ["BaseContainer", "NodeNG", "const_factory"]
    ],
)
@pytest.mark.filterwarnings("error")
def test_str_repr_no_warnings(node):
    parameters = inspect.signature(node.__init__).parameters

    args = {}
    for name, param_type in parameters.items():
        if name == "self":
            continue

        if "int" in param_type.annotation:
            args[name] = random.randint(0, 50)
        elif (
            "NodeNG" in param_type.annotation
            or "SuccessfulInferenceResult" in param_type.annotation
        ):
            args[name] = nodes.Unknown()
        elif "str" in param_type.annotation:
            args[name] = ""
        else:
            args[name] = None

    test_node = node(**args)
    str(test_node)
    repr(test_node)


def test_arguments_contains_all():
    """Ensure Arguments.arguments actually returns all available arguments"""

    def manually_get_args(arg_node) -> set:
        names = set()
        if arg_node.args.vararg:
            names.add(arg_node.args.vararg)
        if arg_node.args.kwarg:
            names.add(arg_node.args.kwarg)

        names.update([x.name for x in arg_node.args.args])
        names.update([x.name for x in arg_node.args.kwonlyargs])

        return names

    node = extract_node("""def a(fruit: str, *args, b=None, c=None, **kwargs): ...""")
    assert manually_get_args(node) == {x.name for x in node.args.arguments}

    node = extract_node("""def a(mango: int, b="banana", c=None, **kwargs): ...""")
    assert manually_get_args(node) == {x.name for x in node.args.arguments}

    node = extract_node("""def a(self, num = 10, *args): ...""")
    assert manually_get_args(node) == {x.name for x in node.args.arguments}


def test_arguments_default_value():
    node = extract_node(
        "def fruit(eat='please', *, peel='no', trim='yes', **kwargs): ..."
    )
    assert node.args.default_value("eat").value == "please"

    node = extract_node("def fruit(seeds, flavor='good', *, peel='maybe'): ...")
    assert node.args.default_value("flavor").value == "good"
