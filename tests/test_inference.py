# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Tests for the astroid inference capabilities."""

from __future__ import annotations

import sys
import textwrap
import unittest
from abc import ABCMeta
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from astroid import (
    Assign,
    Const,
    Slice,
    Uninferable,
    arguments,
    manager,
    nodes,
    objects,
    test_utils,
    util,
)
from astroid import decorators as decoratorsmod
from astroid.arguments import CallSite
from astroid.bases import BoundMethod, Generator, Instance, UnboundMethod, UnionType
from astroid.builder import AstroidBuilder, _extract_single_node, extract_node, parse
from astroid.const import IS_PYPY, PY310_PLUS, PY312_PLUS
from astroid.context import CallContext, InferenceContext
from astroid.exceptions import (
    AstroidTypeError,
    AttributeInferenceError,
    InferenceError,
    NoDefault,
    NotFoundError,
)
from astroid.objects import ExceptionInstance

from . import resources

try:
    import six  # type: ignore[import]  # pylint: disable=unused-import

    HAS_SIX = True
except ImportError:
    HAS_SIX = False


def get_node_of_class(start_from: nodes.FunctionDef, klass: type) -> nodes.Attribute:
    return next(start_from.nodes_of_class(klass))


builder = AstroidBuilder()

DATA_DIR = Path(__file__).parent / "testdata" / "python3" / "data"


class InferenceUtilsTest(unittest.TestCase):
    def test_path_wrapper(self) -> None:
        def infer_default(self: Any, *args: InferenceContext) -> None:
            raise InferenceError

        infer_default = decoratorsmod.path_wrapper(infer_default)
        infer_end = decoratorsmod.path_wrapper(Slice._infer)
        with self.assertRaises(InferenceError):
            next(infer_default(1))
        self.assertEqual(next(infer_end(1)), 1)


def _assertInferElts(
    node_type: ABCMeta,
    self: InferenceTest,
    node: Any,
    elts: list[int] | list[str],
) -> None:
    inferred = next(node.infer())
    self.assertIsInstance(inferred, node_type)
    self.assertEqual(sorted(elt.value for elt in inferred.elts), elts)


def partialmethod(func, arg):
    """similar to functools.partial but return a lambda instead of a class so returned value may be
    turned into a method.
    """
    return lambda *args, **kwargs: func(arg, *args, **kwargs)


class InferenceTest(resources.SysPathSetup, unittest.TestCase):
    # additional assertInfer* method for builtin types

    def assertInferConst(self, node: nodes.Call, expected: str) -> None:
        inferred = next(node.infer())
        self.assertIsInstance(inferred, nodes.Const)
        self.assertEqual(inferred.value, expected)

    def assertInferDict(
        self, node: nodes.Call | nodes.Dict | nodes.NodeNG, expected: Any
    ) -> None:
        inferred = next(node.infer())
        self.assertIsInstance(inferred, nodes.Dict)

        elts = {(key.value, value.value) for (key, value) in inferred.items}
        self.assertEqual(sorted(elts), sorted(expected.items()))

    assertInferTuple = partialmethod(_assertInferElts, nodes.Tuple)
    assertInferList = partialmethod(_assertInferElts, nodes.List)
    assertInferSet = partialmethod(_assertInferElts, nodes.Set)
    assertInferFrozenSet = partialmethod(_assertInferElts, objects.FrozenSet)

    CODE = """
        class C(object):
            "new style"
            attr = 4

            def meth1(self, arg1, optarg=0):
                var = object()
                print ("yo", arg1, optarg)
                self.iattr = "hop"
                return var

            def meth2(self):
                self.meth1(*self.meth3)

            def meth3(self, d=attr):
                b = self.attr
                c = self.iattr
                return b, c

        ex = Exception("msg")
        v = C().meth1(1)
        m_unbound = C.meth1
        m_bound = C().meth1
        a, b, c = ex, 1, "bonjour"
        [d, e, f] = [ex, 1.0, ("bonjour", v)]
        g, h = f
        i, (j, k) = "glup", f

        a, b= b, a # Gasp !
        """

    ast = parse(CODE, __name__)

    def test_arg_keyword_no_default_value(self):
        node = extract_node(
            """
        class Sensor:
            def __init__(self, *, description): #@
                self._id = description.key
        """
        )
        with self.assertRaises(NoDefault):
            node.args.default_value("description")

        node = extract_node("def apple(color, *args, name: str, **kwargs): ...")
        with self.assertRaises(NoDefault):
            node.args.default_value("name")

    def test_infer_abstract_property_return_values(self) -> None:
        module = parse(
            """
        import abc

        class A(object):
            @abc.abstractproperty
            def test(self):
                return 42

        a = A()
        x = a.test
        """
        )
        inferred = next(module["x"].infer())
        self.assertIsInstance(inferred, nodes.Const)
        self.assertEqual(inferred.value, 42)

    def test_module_inference(self) -> None:
        inferred = self.ast.infer()
        obj = next(inferred)
        self.assertEqual(obj.name, __name__)
        self.assertEqual(obj.root().name, __name__)
        self.assertRaises(StopIteration, partial(next, inferred))

    def test_class_inference(self) -> None:
        inferred = self.ast["C"].infer()
        obj = next(inferred)
        self.assertEqual(obj.name, "C")
        self.assertEqual(obj.root().name, __name__)
        self.assertRaises(StopIteration, partial(next, inferred))

    def test_function_inference(self) -> None:
        inferred = self.ast["C"]["meth1"].infer()
        obj = next(inferred)
        self.assertEqual(obj.name, "meth1")
        self.assertEqual(obj.root().name, __name__)
        self.assertRaises(StopIteration, partial(next, inferred))

    def test_builtin_name_inference(self) -> None:
        inferred = self.ast["C"]["meth1"]["var"].infer()
        var = next(inferred)
        self.assertEqual(var.name, "object")
        self.assertEqual(var.root().name, "builtins")
        self.assertRaises(StopIteration, partial(next, inferred))

    def test_tupleassign_name_inference(self) -> None:
        inferred = self.ast["a"].infer()
        exc = next(inferred)
        self.assertIsInstance(exc, Instance)
        self.assertEqual(exc.name, "Exception")
        self.assertEqual(exc.root().name, "builtins")
        self.assertRaises(StopIteration, partial(next, inferred))
        inferred = self.ast["b"].infer()
        const = next(inferred)
        self.assertIsInstance(const, nodes.Const)
        self.assertEqual(const.value, 1)
        self.assertRaises(StopIteration, partial(next, inferred))
        inferred = self.ast["c"].infer()
        const = next(inferred)
        self.assertIsInstance(const, nodes.Const)
        self.assertEqual(const.value, "bonjour")
        self.assertRaises(StopIteration, partial(next, inferred))

    def test_listassign_name_inference(self) -> None:
        inferred = self.ast["d"].infer()
        exc = next(inferred)
        self.assertIsInstance(exc, Instance)
        self.assertEqual(exc.name, "Exception")
        self.assertEqual(exc.root().name, "builtins")
        self.assertRaises(StopIteration, partial(next, inferred))
        inferred = self.ast["e"].infer()
        const = next(inferred)
        self.assertIsInstance(const, nodes.Const)
        self.assertEqual(const.value, 1.0)
        self.assertRaises(StopIteration, partial(next, inferred))
        inferred = self.ast["f"].infer()
        const = next(inferred)
        self.assertIsInstance(const, nodes.Tuple)
        self.assertRaises(StopIteration, partial(next, inferred))

    def test_advanced_tupleassign_name_inference1(self) -> None:
        inferred = self.ast["g"].infer()
        const = next(inferred)
        self.assertIsInstance(const, nodes.Const)
        self.assertEqual(const.value, "bonjour")
        self.assertRaises(StopIteration, partial(next, inferred))
        inferred = self.ast["h"].infer()
        var = next(inferred)
        self.assertEqual(var.name, "object")
        self.assertEqual(var.root().name, "builtins")
        self.assertRaises(StopIteration, partial(next, inferred))

    def test_advanced_tupleassign_name_inference2(self) -> None:
        inferred = self.ast["i"].infer()
        const = next(inferred)
        self.assertIsInstance(const, nodes.Const)
        self.assertEqual(const.value, "glup")
        self.assertRaises(StopIteration, partial(next, inferred))
        inferred = self.ast["j"].infer()
        const = next(inferred)
        self.assertIsInstance(const, nodes.Const)
        self.assertEqual(const.value, "bonjour")
        self.assertRaises(StopIteration, partial(next, inferred))
        inferred = self.ast["k"].infer()
        var = next(inferred)
        self.assertEqual(var.name, "object")
        self.assertEqual(var.root().name, "builtins")
        self.assertRaises(StopIteration, partial(next, inferred))

    def test_swap_assign_inference(self) -> None:
        inferred = self.ast.locals["a"][1].infer()
        const = next(inferred)
        self.assertIsInstance(const, nodes.Const)
        self.assertEqual(const.value, 1)
        self.assertRaises(StopIteration, partial(next, inferred))
        inferred = self.ast.locals["b"][1].infer()
        exc = next(inferred)
        self.assertIsInstance(exc, Instance)
        self.assertEqual(exc.name, "Exception")
        self.assertEqual(exc.root().name, "builtins")
        self.assertRaises(StopIteration, partial(next, inferred))

    def test_getattr_inference1(self) -> None:
        inferred = self.ast["ex"].infer()
        exc = next(inferred)
        self.assertIsInstance(exc, Instance)
        self.assertEqual(exc.name, "Exception")
        self.assertEqual(exc.root().name, "builtins")
        self.assertRaises(StopIteration, partial(next, inferred))

    def test_getattr_inference2(self) -> None:
        inferred = get_node_of_class(self.ast["C"]["meth2"], nodes.Attribute).infer()
        meth1 = next(inferred)
        self.assertEqual(meth1.name, "meth1")
        self.assertEqual(meth1.root().name, __name__)
        self.assertRaises(StopIteration, partial(next, inferred))

    def test_getattr_inference3(self) -> None:
        inferred = self.ast["C"]["meth3"]["b"].infer()
        const = next(inferred)
        self.assertIsInstance(const, nodes.Const)
        self.assertEqual(const.value, 4)
        self.assertRaises(StopIteration, partial(next, inferred))

    def test_getattr_inference4(self) -> None:
        inferred = self.ast["C"]["meth3"]["c"].infer()
        const = next(inferred)
        self.assertIsInstance(const, nodes.Const)
        self.assertEqual(const.value, "hop")
        self.assertRaises(StopIteration, partial(next, inferred))

    def test_callfunc_inference(self) -> None:
        inferred = self.ast["v"].infer()
        meth1 = next(inferred)
        self.assertIsInstance(meth1, Instance)
        self.assertEqual(meth1.name, "object")
        self.assertEqual(meth1.root().name, "builtins")
        self.assertRaises(StopIteration, partial(next, inferred))

    def test_unbound_method_inference(self) -> None:
        inferred = self.ast["m_unbound"].infer()
        meth1 = next(inferred)
        self.assertIsInstance(meth1, UnboundMethod)
        self.assertEqual(meth1.name, "meth1")
        self.assertEqual(meth1.parent.frame().name, "C")
        self.assertEqual(meth1.parent.frame().name, "C")
        self.assertRaises(StopIteration, partial(next, inferred))

    def test_bound_method_inference(self) -> None:
        inferred = self.ast["m_bound"].infer()
        meth1 = next(inferred)
        self.assertIsInstance(meth1, BoundMethod)
        self.assertEqual(meth1.name, "meth1")
        self.assertEqual(meth1.parent.frame().name, "C")
        self.assertEqual(meth1.parent.frame().name, "C")
        self.assertRaises(StopIteration, partial(next, inferred))

    def test_args_default_inference1(self) -> None:
        optarg = test_utils.get_name_node(self.ast["C"]["meth1"], "optarg")
        inferred = optarg.infer()
        obj1 = next(inferred)
        self.assertIsInstance(obj1, nodes.Const)
        self.assertEqual(obj1.value, 0)
        obj1 = next(inferred)
        self.assertIs(obj1, util.Uninferable, obj1)
        self.assertRaises(StopIteration, partial(next, inferred))

    def test_args_default_inference2(self) -> None:
        inferred = self.ast["C"]["meth3"].ilookup("d")
        obj1 = next(inferred)
        self.assertIsInstance(obj1, nodes.Const)
        self.assertEqual(obj1.value, 4)
        obj1 = next(inferred)
        self.assertIs(obj1, util.Uninferable, obj1)
        self.assertRaises(StopIteration, partial(next, inferred))

    def test_inference_restrictions(self) -> None:
        inferred = test_utils.get_name_node(self.ast["C"]["meth1"], "arg1").infer()
        obj1 = next(inferred)
        self.assertIs(obj1, util.Uninferable, obj1)
        self.assertRaises(StopIteration, partial(next, inferred))

    def test_ancestors_inference(self) -> None:
        code = """
            class A(object):  #@
                pass

            class A(A):  #@
                pass
        """
        a1, a2 = extract_node(code, __name__)
        a2_ancestors = list(a2.ancestors())
        self.assertEqual(len(a2_ancestors), 2)
        self.assertIs(a2_ancestors[0], a1)

    def test_ancestors_inference2(self) -> None:
        code = """
            class A(object):  #@
                pass

            class B(A):  #@
                pass

            class A(B):  #@
                pass
        """
        a1, b, a2 = extract_node(code, __name__)
        a2_ancestors = list(a2.ancestors())
        self.assertEqual(len(a2_ancestors), 3)
        self.assertIs(a2_ancestors[0], b)
        self.assertIs(a2_ancestors[1], a1)

    def test_f_arg_f(self) -> None:
        code = """
            def f(f=1):
                return f

            a = f()
        """
        ast = parse(code, __name__)
        a = ast["a"]
        a_inferred = a.inferred()
        self.assertEqual(a_inferred[0].value, 1)
        self.assertEqual(len(a_inferred), 1)

    def test_exc_ancestors(self) -> None:
        code = """
        def f():
            raise __(NotImplementedError)
        """
        error = extract_node(code, __name__)
        nie = error.inferred()[0]
        self.assertIsInstance(nie, nodes.ClassDef)
        nie_ancestors = [c.name for c in nie.ancestors()]
        expected = ["RuntimeError", "Exception", "BaseException", "object"]
        self.assertEqual(nie_ancestors, expected)

    def test_except_inference(self) -> None:
        code = """
            try:
                print (hop)
            except NameError as ex:
                ex1 = ex
            except Exception as ex:
                ex2 = ex
                raise
        """
        ast = parse(code, __name__)
        ex1 = ast["ex1"]
        ex1_infer = ex1.infer()
        ex1 = next(ex1_infer)
        self.assertIsInstance(ex1, Instance)
        self.assertEqual(ex1.name, "NameError")
        self.assertRaises(StopIteration, partial(next, ex1_infer))
        ex2 = ast["ex2"]
        ex2_infer = ex2.infer()
        ex2 = next(ex2_infer)
        self.assertIsInstance(ex2, Instance)
        self.assertEqual(ex2.name, "Exception")
        self.assertRaises(StopIteration, partial(next, ex2_infer))

    def test_del1(self) -> None:
        code = """
            del undefined_attr
        """
        delete = extract_node(code, __name__)
        self.assertRaises(InferenceError, next, delete.infer())

    def test_del2(self) -> None:
        code = """
            a = 1
            b = a
            del a
            c = a
            a = 2
            d = a
        """
        ast = parse(code, __name__)
        n = ast["b"]
        n_infer = n.infer()
        inferred = next(n_infer)
        self.assertIsInstance(inferred, nodes.Const)
        self.assertEqual(inferred.value, 1)
        self.assertRaises(StopIteration, partial(next, n_infer))
        n = ast["c"]
        n_infer = n.infer()
        self.assertRaises(InferenceError, partial(next, n_infer))
        n = ast["d"]
        n_infer = n.infer()
        inferred = next(n_infer)
        self.assertIsInstance(inferred, nodes.Const)
        self.assertEqual(inferred.value, 2)
        self.assertRaises(StopIteration, partial(next, n_infer))

    def test_builtin_types(self) -> None:
        code = """
            l = [1]
            t = (2,)
            d = {}
            s = ''
            s2 = '_'
        """
        ast = parse(code, __name__)
        n = ast["l"]
        inferred = next(n.infer())
        self.assertIsInstance(inferred, nodes.List)
        self.assertIsInstance(inferred, Instance)
        self.assertEqual(inferred.getitem(nodes.Const(0)).value, 1)
        self.assertIsInstance(inferred._proxied, nodes.ClassDef)
        self.assertEqual(inferred._proxied.name, "list")
        self.assertIn("append", inferred._proxied.locals)
        n = ast["t"]
        inferred = next(n.infer())
        self.assertIsInstance(inferred, nodes.Tuple)
        self.assertIsInstance(inferred, Instance)
        self.assertEqual(inferred.getitem(nodes.Const(0)).value, 2)
        self.assertIsInstance(inferred._proxied, nodes.ClassDef)
        self.assertEqual(inferred._proxied.name, "tuple")
        n = ast["d"]
        inferred = next(n.infer())
        self.assertIsInstance(inferred, nodes.Dict)
        self.assertIsInstance(inferred, Instance)
        self.assertIsInstance(inferred._proxied, nodes.ClassDef)
        self.assertEqual(inferred._proxied.name, "dict")
        self.assertIn("get", inferred._proxied.locals)
        n = ast["s"]
        inferred = next(n.infer())
        self.assertIsInstance(inferred, nodes.Const)
        self.assertIsInstance(inferred, Instance)
        self.assertEqual(inferred.name, "str")
        self.assertIn("lower", inferred._proxied.locals)
        n = ast["s2"]
        inferred = next(n.infer())
        self.assertEqual(inferred.getitem(nodes.Const(0)).value, "_")

        code = "s = {1}"
        ast = parse(code, __name__)
        n = ast["s"]
        inferred = next(n.infer())
        self.assertIsInstance(inferred, nodes.Set)
        self.assertIsInstance(inferred, Instance)
        self.assertEqual(inferred.name, "set")
        self.assertIn("remove", inferred._proxied.locals)

    @pytest.mark.xfail(reason="Descriptors are not properly inferred as callable")
    def test_descriptor_are_callable(self):
        code = """
            class A:
                statm = staticmethod(open)
                clsm = classmethod('whatever')
        """
        ast = parse(code, __name__)
        statm = next(ast["A"].igetattr("statm"))
        self.assertTrue(statm.callable())
        clsm = next(ast["A"].igetattr("clsm"))
        self.assertFalse(clsm.callable())

    def test_bt_ancestor_crash(self) -> None:
        code = """
            class Warning(Warning):
                pass
        """
        ast = parse(code, __name__)
        w = ast["Warning"]
        ancestors = w.ancestors()
        ancestor = next(ancestors)
        self.assertEqual(ancestor.name, "Warning")
        self.assertEqual(ancestor.root().name, "builtins")
        ancestor = next(ancestors)
        self.assertEqual(ancestor.name, "Exception")
        self.assertEqual(ancestor.root().name, "builtins")
        ancestor = next(ancestors)
        self.assertEqual(ancestor.name, "BaseException")
        self.assertEqual(ancestor.root().name, "builtins")
        ancestor = next(ancestors)
        self.assertEqual(ancestor.name, "object")
        self.assertEqual(ancestor.root().name, "builtins")
        self.assertRaises(StopIteration, partial(next, ancestors))

    def test_method_argument(self) -> None:
        code = '''
            class ErudiEntitySchema:
                """an entity has a type, a set of subject and or object relations"""
                def __init__(self, e_type, **kwargs):
                    kwargs['e_type'] = e_type.capitalize().encode()

                def meth(self, e_type, *args, **kwargs):
                    kwargs['e_type'] = e_type.capitalize().encode()
                    print(args)
            '''
        ast = parse(code, __name__)
        arg = test_utils.get_name_node(ast["ErudiEntitySchema"]["__init__"], "e_type")
        self.assertEqual(
            [n.__class__ for n in arg.infer()], [util.Uninferable.__class__]
        )
        arg = test_utils.get_name_node(ast["ErudiEntitySchema"]["__init__"], "kwargs")
        self.assertEqual([n.__class__ for n in arg.infer()], [nodes.Dict])
        arg = test_utils.get_name_node(ast["ErudiEntitySchema"]["meth"], "e_type")
        self.assertEqual(
            [n.__class__ for n in arg.infer()], [util.Uninferable.__class__]
        )
        arg = test_utils.get_name_node(ast["ErudiEntitySchema"]["meth"], "args")
        self.assertEqual([n.__class__ for n in arg.infer()], [nodes.Tuple])
        arg = test_utils.get_name_node(ast["ErudiEntitySchema"]["meth"], "kwargs")
        self.assertEqual([n.__class__ for n in arg.infer()], [nodes.Dict])

    def test_tuple_then_list(self) -> None:
        code = """
            def test_view(rql, vid, tags=()):
                tags = list(tags)
                __(tags).append(vid)
        """
        name = extract_node(code, __name__)
        it = name.infer()
        tags = next(it)
        self.assertIsInstance(tags, nodes.List)
        self.assertEqual(tags.elts, [])
        with self.assertRaises(StopIteration):
            next(it)

    def test_mulassign_inference(self) -> None:
        code = '''
            def first_word(line):
                """Return the first word of a line"""

                return line.split()[0]

            def last_word(line):
                """Return last word of a line"""

                return line.split()[-1]

            def process_line(word_pos):
                """Silly function: returns (ok, callable) based on argument.

                   For test purpose only.
                """

                if word_pos > 0:
                    return (True, first_word)
                elif word_pos < 0:
                    return  (True, last_word)
                else:
                    return (False, None)

            if __name__ == '__main__':

                line_number = 0
                for a_line in file('test_callable.py'):
                    tupletest  = process_line(line_number)
                    (ok, fct)  = process_line(line_number)
                    if ok:
                        fct(a_line)
        '''
        ast = parse(code, __name__)
        self.assertEqual(len(list(ast["process_line"].infer_call_result(None))), 3)
        self.assertEqual(len(list(ast["tupletest"].infer())), 3)
        values = [
            "<FunctionDef.first_word",
            "<FunctionDef.last_word",
            "<Const.NoneType",
        ]
        self.assertTrue(
            all(
                repr(inferred).startswith(value)
                for inferred, value in zip(ast["fct"].infer(), values)
            )
        )

    def test_fstring_inference(self) -> None:
        code = """
            name = "John"
            result = f"Hello {name}!"
            """
        ast = parse(code, __name__)
        node = ast["result"]
        inferred = node.inferred()
        self.assertEqual(len(inferred), 1)
        value_node = inferred[0]
        self.assertIsInstance(value_node, Const)
        self.assertEqual(value_node.value, "Hello John!")

    def test_float_complex_ambiguity(self) -> None:
        code = '''
            def no_conjugate_member(magic_flag):  #@
                """should not raise E1101 on something.conjugate"""
                if magic_flag:
                    something = 1.0
                else:
                    something = 1.0j
                if isinstance(something, float):
                    return something
                return __(something).conjugate()
        '''
        func, retval = extract_node(code, __name__)
        self.assertEqual([i.value for i in func.ilookup("something")], [1.0, 1.0j])
        self.assertEqual([i.value for i in retval.infer()], [1.0, 1.0j])

    def test_lookup_cond_branches(self) -> None:
        code = '''
            def no_conjugate_member(magic_flag):
                """should not raise E1101 on something.conjugate"""
                something = 1.0
                if magic_flag:
                    something = 1.0j
                return something.conjugate()
        '''
        ast = parse(code, __name__)
        values = [
            i.value for i in test_utils.get_name_node(ast, "something", -1).infer()
        ]
        self.assertEqual(values, [1.0, 1.0j])

    def test_simple_subscript(self) -> None:
        code = """
            class A(object):
                def __getitem__(self, index):
                    return index + 42
            [1, 2, 3][0] #@
            (1, 2, 3)[1] #@
            (1, 2, 3)[-1] #@
            [1, 2, 3][0] + (2, )[0] + (3, )[-1] #@
            e = {'key': 'value'}
            e['key'] #@
            "first"[0] #@
            list([1, 2, 3])[-1] #@
            tuple((4, 5, 6))[2] #@
            A()[0] #@
            A()[-1] #@
        """
        ast_nodes = extract_node(code, __name__)
        expected = [1, 2, 3, 6, "value", "f", 3, 6, 42, 41]
        for node, expected_value in zip(ast_nodes, expected):
            inferred = next(node.infer())
            self.assertIsInstance(inferred, nodes.Const)
            self.assertEqual(inferred.value, expected_value)

    def test_invalid_subscripts(self) -> None:
        ast_nodes = extract_node(
            """
        class NoGetitem(object):
            pass
        class InvalidGetitem(object):
            def __getitem__(self): pass
        class InvalidGetitem2(object):
            __getitem__ = 42
        NoGetitem()[4] #@
        InvalidGetitem()[5] #@
        InvalidGetitem2()[10] #@
        [1, 2, 3][None] #@
        'lala'['bala'] #@
        """
        )
        for node in ast_nodes:
            self.assertRaises(InferenceError, next, node.infer())

    def test_bytes_subscript(self) -> None:
        node = extract_node("""b'a'[0]""")
        inferred = next(node.infer())
        self.assertIsInstance(inferred, nodes.Const)
        self.assertEqual(inferred.value, 97)

    def test_subscript_multi_value(self) -> None:
        code = """
            def do_thing_with_subscript(magic_flag):
                src = [3, 2, 1]
                if magic_flag:
                    src = [1, 2, 3]
                something = src[0]
                return something
        """
        ast = parse(code, __name__)
        values = [
            i.value for i in test_utils.get_name_node(ast, "something", -1).infer()
        ]
        self.assertEqual(list(sorted(values)), [1, 3])

    def test_subscript_multi_slice(self) -> None:
        code = """
            def zero_or_one(magic_flag):
                if magic_flag:
                    return 1
                return 0

            def do_thing_with_subscript(magic_flag):
                src = [3, 2, 1]
                index = zero_or_one(magic_flag)
                something = src[index]
                return something
        """
        ast = parse(code, __name__)
        values = [
            i.value for i in test_utils.get_name_node(ast, "something", -1).infer()
        ]
        self.assertEqual(list(sorted(values)), [2, 3])

    def test_simple_tuple(self) -> None:
        module = parse(
            """
        a = (1,)
        b = (22,)
        some = a + b #@
        """
        )
        ast = next(module["some"].infer())
        self.assertIsInstance(ast, nodes.Tuple)
        self.assertEqual(len(ast.elts), 2)
        self.assertEqual(ast.elts[0].value, 1)
        self.assertEqual(ast.elts[1].value, 22)

    def test_simple_for(self) -> None:
        code = """
            for a in [1, 2, 3]:
                print (a)
            for b,c in [(1,2), (3,4)]:
                print (b)
                print (c)

            print ([(d,e) for e,d in ([1,2], [3,4])])
        """
        ast = parse(code, __name__)
        self.assertEqual(
            [i.value for i in test_utils.get_name_node(ast, "a", -1).infer()], [1, 2, 3]
        )
        self.assertEqual(
            [i.value for i in test_utils.get_name_node(ast, "b", -1).infer()], [1, 3]
        )
        self.assertEqual(
            [i.value for i in test_utils.get_name_node(ast, "c", -1).infer()], [2, 4]
        )
        self.assertEqual(
            [i.value for i in test_utils.get_name_node(ast, "d", -1).infer()], [2, 4]
        )
        self.assertEqual(
            [i.value for i in test_utils.get_name_node(ast, "e", -1).infer()], [1, 3]
        )

    def test_simple_for_genexpr(self) -> None:
        code = """
            print ((d,e) for e,d in ([1,2], [3,4]))
        """
        ast = parse(code, __name__)
        self.assertEqual(
            [i.value for i in test_utils.get_name_node(ast, "d", -1).infer()], [2, 4]
        )
        self.assertEqual(
            [i.value for i in test_utils.get_name_node(ast, "e", -1).infer()], [1, 3]
        )

    def test_for_dict(self) -> None:
        code = """
            for a, b in {1: 2, 3: 4}.items():
                print(a)
                print(b)

            for c, (d, e) in {1: (2, 3), 4: (5, 6)}.items():
                print(c)
                print(d)
                print(e)

            print([(f, g, h) for f, (g, h) in {1: (2, 3), 4: (5, 6)}.items()])
        """
        ast = parse(code, __name__)
        self.assertEqual(
            [i.value for i in test_utils.get_name_node(ast, "a", -1).infer()], [1, 3]
        )
        self.assertEqual(
            [i.value for i in test_utils.get_name_node(ast, "b", -1).infer()], [2, 4]
        )
        self.assertEqual(
            [i.value for i in test_utils.get_name_node(ast, "c", -1).infer()], [1, 4]
        )
        self.assertEqual(
            [i.value for i in test_utils.get_name_node(ast, "d", -1).infer()], [2, 5]
        )
        self.assertEqual(
            [i.value for i in test_utils.get_name_node(ast, "e", -1).infer()], [3, 6]
        )
        self.assertEqual(
            [i.value for i in test_utils.get_name_node(ast, "f", -1).infer()], [1, 4]
        )
        self.assertEqual(
            [i.value for i in test_utils.get_name_node(ast, "g", -1).infer()], [2, 5]
        )
        self.assertEqual(
            [i.value for i in test_utils.get_name_node(ast, "h", -1).infer()], [3, 6]
        )

    def test_builtin_help(self) -> None:
        code = """
            help()
        """
        # XXX failing since __builtin__.help assignment has
        #     been moved into a function...
        node = extract_node(code, __name__)
        inferred = list(node.func.infer())
        self.assertEqual(len(inferred), 1, inferred)
        self.assertIsInstance(inferred[0], Instance)
        self.assertEqual(inferred[0].name, "_Helper")

    def test_builtin_open(self) -> None:
        code = """
            open("toto.txt")
        """
        node = extract_node(code, __name__).func
        inferred = list(node.infer())
        self.assertEqual(len(inferred), 1)
        self.assertIsInstance(inferred[0], nodes.FunctionDef)
        self.assertEqual(inferred[0].name, "open")

    def test_callfunc_context_func(self) -> None:
        code = """
            def mirror(arg=None):
                return arg

            un = mirror(1)
        """
        ast = parse(code, __name__)
        inferred = list(ast.igetattr("un"))
        self.assertEqual(len(inferred), 1)
        self.assertIsInstance(inferred[0], nodes.Const)
        self.assertEqual(inferred[0].value, 1)

    def test_callfunc_context_lambda(self) -> None:
        code = """
            mirror = lambda x=None: x

            un = mirror(1)
        """
        ast = parse(code, __name__)
        inferred = list(ast.igetattr("mirror"))
        self.assertEqual(len(inferred), 1)
        self.assertIsInstance(inferred[0], nodes.Lambda)
        inferred = list(ast.igetattr("un"))
        self.assertEqual(len(inferred), 1)
        self.assertIsInstance(inferred[0], nodes.Const)
        self.assertEqual(inferred[0].value, 1)

    def test_factory_method(self) -> None:
        code = """
            class Super(object):
                  @classmethod
                  def instance(cls):
                          return cls()

            class Sub(Super):
                  def method(self):
                          print ('method called')

            sub = Sub.instance()
        """
        ast = parse(code, __name__)
        inferred = list(ast.igetattr("sub"))
        self.assertEqual(len(inferred), 1)
        self.assertIsInstance(inferred[0], Instance)
        self.assertEqual(inferred[0]._proxied.name, "Sub")

    def test_factory_methods_cls_call(self) -> None:
        ast = extract_node(
            """
        class C:
            @classmethod
            def factory(cls):
                return cls()

        class D(C):
            pass

        C.factory() #@
        D.factory() #@
        """,
            "module",
        )
        should_be_c = list(ast[0].infer())
        should_be_d = list(ast[1].infer())
        self.assertEqual(1, len(should_be_c))
        self.assertEqual(1, len(should_be_d))
        self.assertEqual("module.C", should_be_c[0].qname())
        self.assertEqual("module.D", should_be_d[0].qname())

    def test_factory_methods_object_new_call(self) -> None:
        ast = extract_node(
            """
        class C:
            @classmethod
            def factory(cls):
                return object.__new__(cls)

        class D(C):
            pass

        C.factory() #@
        D.factory() #@
        """,
            "module",
        )
        should_be_c = list(ast[0].infer())
        should_be_d = list(ast[1].infer())
        self.assertEqual(1, len(should_be_c))
        self.assertEqual(1, len(should_be_d))
        self.assertEqual("module.C", should_be_c[0].qname())
        self.assertEqual("module.D", should_be_d[0].qname())

    @pytest.mark.xfail(
        reason="pathlib.Path cannot be inferred on Python 3.8",
    )
    def test_factory_methods_inside_binary_operation(self):
        node = extract_node(
            """
        from pathlib import Path
        h = Path("/home")
        u = h / "user"
        u #@
        """
        )
        assert next(node.infer()).qname() == "pathlib.Path"

    def test_import_as(self) -> None:
        code = """
            import os.path as osp
            print (osp.dirname(__file__))

            from os.path import exists as e
            assert e(__file__)
        """
        ast = parse(code, __name__)
        inferred = list(ast.igetattr("osp"))
        self.assertEqual(len(inferred), 1)
        self.assertIsInstance(inferred[0], nodes.Module)
        self.assertEqual(inferred[0].name, "os.path")
        inferred = list(ast.igetattr("e"))
        if PY312_PLUS and sys.platform.startswith("win"):
            # There are two os.path.exists exported, likely due to
            # https://github.com/python/cpython/pull/101324
            self.assertEqual(len(inferred), 2)
        else:
            self.assertEqual(len(inferred), 1)
        self.assertIsInstance(inferred[0], nodes.FunctionDef)
        self.assertEqual(inferred[0].name, "exists")

    def test_do_import_module_performance(self) -> None:
        import_node = extract_node("import importlib")
        import_node.modname = ""
        import_node.do_import_module()
        # calling file_from_module_name() indicates we didn't hit the cache
        with unittest.mock.patch.object(
            manager.AstroidManager, "file_from_module_name", side_effect=AssertionError
        ):
            import_node.do_import_module()

    def _test_const_inferred(self, node: nodes.AssignName, value: float | str) -> None:
        inferred = list(node.infer())
        self.assertEqual(len(inferred), 1)
        self.assertIsInstance(inferred[0], nodes.Const)
        self.assertEqual(inferred[0].value, value)

    def test_unary_not(self) -> None:
        for code in (
            "a = not (1,); b = not ()",
            "a = not {1:2}; b = not {}",
            "a = not [1, 2]; b = not []",
            "a = not {1, 2}; b = not set()",
            "a = not 1; b = not 0",
            'a = not "a"; b = not ""',
            'a = not b"a"; b = not b""',
        ):
            ast = builder.string_build(code, __name__, __file__)
            self._test_const_inferred(ast["a"], False)
            self._test_const_inferred(ast["b"], True)

    def test_unary_op_numbers(self) -> None:
        ast_nodes = extract_node(
            """
        +1 #@
        -1 #@
        ~1 #@
        +2.0 #@
        -2.0 #@
        """
        )
        expected = [1, -1, -2, 2.0, -2.0]
        for node, expected_value in zip(ast_nodes, expected):
            inferred = next(node.infer())
            self.assertEqual(inferred.value, expected_value)

    def test_matmul(self) -> None:
        node = extract_node(
            """
        class Array:
            def __matmul__(self, other):
                return 42
        Array() @ Array() #@
        """
        )
        inferred = next(node.infer())
        self.assertIsInstance(inferred, nodes.Const)
        self.assertEqual(inferred.value, 42)

    def test_binary_op_int_add(self) -> None:
        ast = builder.string_build("a = 1 + 2", __name__, __file__)
        self._test_const_inferred(ast["a"], 3)

    def test_binary_op_int_sub(self) -> None:
        ast = builder.string_build("a = 1 - 2", __name__, __file__)
        self._test_const_inferred(ast["a"], -1)

    def test_binary_op_float_div(self) -> None:
        ast = builder.string_build("a = 1 / 2.", __name__, __file__)
        self._test_const_inferred(ast["a"], 1 / 2.0)

    def test_binary_op_str_mul(self) -> None:
        ast = builder.string_build('a = "*" * 40', __name__, __file__)
        self._test_const_inferred(ast["a"], "*" * 40)

    def test_binary_op_int_bitand(self) -> None:
        ast = builder.string_build("a = 23&20", __name__, __file__)
        self._test_const_inferred(ast["a"], 23 & 20)

    def test_binary_op_int_bitor(self) -> None:
        ast = builder.string_build("a = 23|8", __name__, __file__)
        self._test_const_inferred(ast["a"], 23 | 8)

    def test_binary_op_int_bitxor(self) -> None:
        ast = builder.string_build("a = 23^9", __name__, __file__)
        self._test_const_inferred(ast["a"], 23 ^ 9)

    def test_binary_op_int_shiftright(self) -> None:
        ast = builder.string_build("a = 23 >>1", __name__, __file__)
        self._test_const_inferred(ast["a"], 23 >> 1)

    def test_binary_op_int_shiftleft(self) -> None:
        ast = builder.string_build("a = 23 <<1", __name__, __file__)
        self._test_const_inferred(ast["a"], 23 << 1)

    def test_binary_op_other_type(self) -> None:
        ast_nodes = extract_node(
            """
        class A:
            def __add__(self, other):
                return other + 42
        A() + 1 #@
        1 + A() #@
        """
        )
        assert isinstance(ast_nodes, list)
        first = next(ast_nodes[0].infer())
        self.assertIsInstance(first, nodes.Const)
        self.assertEqual(first.value, 43)

        second = next(ast_nodes[1].infer())
        self.assertEqual(second, util.Uninferable)

    def test_binary_op_other_type_using_reflected_operands(self) -> None:
        ast_nodes = extract_node(
            """
        class A(object):
            def __radd__(self, other):
                return other + 42
        A() + 1 #@
        1 + A() #@
        """
        )
        assert isinstance(ast_nodes, list)
        first = next(ast_nodes[0].infer())
        self.assertEqual(first, util.Uninferable)

        second = next(ast_nodes[1].infer())
        self.assertIsInstance(second, nodes.Const)
        self.assertEqual(second.value, 43)

    def test_binary_op_reflected_and_not_implemented_is_type_error(self) -> None:
        ast_node = extract_node(
            """
        class A(object):
            def __radd__(self, other): return NotImplemented

        1 + A() #@
        """
        )
        first = next(ast_node.infer())
        self.assertEqual(first, util.Uninferable)

    @pytest.mark.filterwarnings("error::DeprecationWarning")
    def test_binary_op_not_used_in_boolean_context(self) -> None:
        ast_node = extract_node("not NotImplemented")
        first = next(ast_node.infer())
        self.assertIsInstance(first, nodes.Const)

    def test_binary_op_list_mul(self) -> None:
        for code in ("a = [[]] * 2", "a = 2 * [[]]"):
            ast = builder.string_build(code, __name__, __file__)
            inferred = list(ast["a"].infer())
            self.assertEqual(len(inferred), 1)
            self.assertIsInstance(inferred[0], nodes.List)
            self.assertEqual(len(inferred[0].elts), 2)
            self.assertIsInstance(inferred[0].elts[0], nodes.List)
            self.assertIsInstance(inferred[0].elts[1], nodes.List)

    def test_binary_op_list_mul_none(self) -> None:
        """Test correct handling on list multiplied by None."""
        ast = builder.string_build('a = [1] * None\nb = [1] * "r"')
        inferred = ast["a"].inferred()
        self.assertEqual(len(inferred), 1)
        self.assertEqual(inferred[0], util.Uninferable)
        inferred = ast["b"].inferred()
        self.assertEqual(len(inferred), 1)
        self.assertEqual(inferred[0], util.Uninferable)

    def test_binary_op_list_mul_int(self) -> None:
        """Test correct handling on list multiplied by int when there are more than one."""
        code = """
        from ctypes import c_int
        seq = [c_int()] * 4
        """
        ast = parse(code, __name__)
        inferred = ast["seq"].inferred()
        self.assertEqual(len(inferred), 1)
        listval = inferred[0]
        self.assertIsInstance(listval, nodes.List)
        self.assertEqual(len(listval.itered()), 4)

    def test_binary_op_on_self(self) -> None:
        """Test correct handling of applying binary operator to self."""
        code = """
        import sys
        sys.path = ['foo'] + sys.path
        sys.path.insert(0, 'bar')
        path = sys.path
        """
        ast = parse(code, __name__)
        inferred = ast["path"].inferred()
        self.assertIsInstance(inferred[0], nodes.List)

    def test_binary_op_tuple_add(self) -> None:
        ast = builder.string_build("a = (1,) + (2,)", __name__, __file__)
        inferred = list(ast["a"].infer())
        self.assertEqual(len(inferred), 1)
        self.assertIsInstance(inferred[0], nodes.Tuple)
        self.assertEqual(len(inferred[0].elts), 2)
        self.assertEqual(inferred[0].elts[0].value, 1)
        self.assertEqual(inferred[0].elts[1].value, 2)

    def test_binary_op_custom_class(self) -> None:
        code = """
        class myarray:
            def __init__(self, array):
                self.array = array
            def __mul__(self, x):
                return myarray([2,4,6])
            def astype(self):
                return "ASTYPE"

        def randint(maximum):
            if maximum is not None:
                return myarray([1,2,3]) * 2
            else:
                return int(5)

        x = randint(1)
        """
        ast = parse(code, __name__)
        inferred = list(ast.igetattr("x"))
        self.assertEqual(len(inferred), 2)
        value = [str(v) for v in inferred]
        # The __name__ trick here makes it work when invoked directly
        # (__name__ == '__main__') and through pytest (__name__ ==
        # 'unittest_inference')
        self.assertEqual(
            value,
            [
                f"Instance of {__name__}.myarray",
                "Const.int(value=5,\n          kind=None)",
            ],
        )

    def test_binary_op_or_union_type(self) -> None:
        """Binary or union is only defined for Python 3.10+."""
        code = """
        class A: ...

        int | 2  #@
        int | "Hello"  #@
        int | ...  #@
        int | A()  #@
        int | None | 2  #@
        """
        ast_nodes = extract_node(code)
        for n in ast_nodes:
            assert n.inferred() == [util.Uninferable]

        code = """
        from typing import List

        class A: ...
        class B: ...

        int | None  #@
        int | str  #@
        int | str | None  #@
        A | B  #@
        A | None  #@
        List[int] | int  #@
        tuple | int  #@
        """
        ast_nodes = extract_node(code)
        if not PY310_PLUS:
            for n in ast_nodes:
                assert n.inferred() == [util.Uninferable]
        else:
            i0 = ast_nodes[0].inferred()[0]
            assert isinstance(i0, UnionType)
            assert isinstance(i0.left, nodes.ClassDef)
            assert i0.left.name == "int"
            assert isinstance(i0.right, nodes.Const)
            assert i0.right.value is None

            # Assert basic UnionType properties and methods
            assert i0.callable() is False
            assert i0.bool_value() is True
            assert i0.pytype() == "types.UnionType"
            assert i0.display_type() == "UnionType"
            assert str(i0) == "UnionType(UnionType)"
            assert repr(i0) == f"<UnionType(UnionType) l.0 at 0x{id(i0)}>"

            i1 = ast_nodes[1].inferred()[0]
            assert isinstance(i1, UnionType)

            i2 = ast_nodes[2].inferred()[0]
            assert isinstance(i2, UnionType)
            assert isinstance(i2.left, UnionType)
            assert isinstance(i2.left.left, nodes.ClassDef)
            assert i2.left.left.name == "int"
            assert isinstance(i2.left.right, nodes.ClassDef)
            assert i2.left.right.name == "str"
            assert isinstance(i2.right, nodes.Const)
            assert i2.right.value is None

            i3 = ast_nodes[3].inferred()[0]
            assert isinstance(i3, UnionType)
            assert isinstance(i3.left, nodes.ClassDef)
            assert i3.left.name == "A"
            assert isinstance(i3.right, nodes.ClassDef)
            assert i3.right.name == "B"

            i4 = ast_nodes[4].inferred()[0]
            assert isinstance(i4, UnionType)

            i5 = ast_nodes[5].inferred()[0]
            assert isinstance(i5, UnionType)
            assert isinstance(i5.left, nodes.ClassDef)
            assert i5.left.name == "List"

            i6 = ast_nodes[6].inferred()[0]
            assert isinstance(i6, UnionType)
            assert isinstance(i6.left, nodes.ClassDef)
            assert i6.left.name == "tuple"

        code = """
        from typing import List

        Alias1 = List[int]
        Alias2 = str | int

        Alias1 | int  #@
        Alias2 | int  #@
        Alias1 | Alias2  #@
        """
        ast_nodes = extract_node(code)
        if not PY310_PLUS:
            for n in ast_nodes:
                assert n.inferred() == [util.Uninferable]
        else:
            i0 = ast_nodes[0].inferred()[0]
            assert isinstance(i0, UnionType)
            assert isinstance(i0.left, nodes.ClassDef)
            assert i0.left.name == "List"

            i1 = ast_nodes[1].inferred()[0]
            assert isinstance(i1, UnionType)
            assert isinstance(i1.left, UnionType)
            assert isinstance(i1.left.left, nodes.ClassDef)
            assert i1.left.left.name == "str"

            i2 = ast_nodes[2].inferred()[0]
            assert isinstance(i2, UnionType)
            assert isinstance(i2.left, nodes.ClassDef)
            assert i2.left.name == "List"
            assert isinstance(i2.right, UnionType)

    def test_nonregr_lambda_arg(self) -> None:
        code = """
        def f(g = lambda: None):
                __(g()).x
"""
        callfuncnode = extract_node(code)
        inferred = list(callfuncnode.infer())
        self.assertEqual(len(inferred), 2, inferred)
        inferred.remove(util.Uninferable)
        self.assertIsInstance(inferred[0], nodes.Const)
        self.assertIsNone(inferred[0].value)

    def test_nonregr_getitem_empty_tuple(self) -> None:
        code = """
            def f(x):
                a = ()[x]
        """
        ast = parse(code, __name__)
        inferred = list(ast["f"].ilookup("a"))
        self.assertEqual(len(inferred), 1)
        self.assertEqual(inferred[0], util.Uninferable)

    def test_nonregr_instance_attrs(self) -> None:
        """Non regression for instance_attrs infinite loop : pylint / #4."""

        code = """
            class Foo(object):

                def set_42(self):
                    self.attr = 42

            class Bar(Foo):

                def __init__(self):
                    self.attr = 41
        """
        ast = parse(code, __name__)
        foo_class = ast["Foo"]
        bar_class = ast["Bar"]
        bar_self = ast["Bar"]["__init__"]["self"]
        assattr = bar_class.instance_attrs["attr"][0]
        self.assertEqual(len(foo_class.instance_attrs["attr"]), 1)
        self.assertEqual(len(bar_class.instance_attrs["attr"]), 1)
        self.assertEqual(bar_class.instance_attrs, {"attr": [assattr]})
        # call 'instance_attr' via 'Instance.getattr' to trigger the bug:
        instance = bar_self.inferred()[0]
        instance.getattr("attr")
        self.assertEqual(len(bar_class.instance_attrs["attr"]), 1)
        self.assertEqual(len(foo_class.instance_attrs["attr"]), 1)
        self.assertEqual(bar_class.instance_attrs, {"attr": [assattr]})

    def test_nonregr_multi_referential_addition(self) -> None:
        """Regression test for https://github.com/pylint-dev/astroid/issues/483
        Make sure issue where referring to the same variable
        in the same inferred expression caused an uninferable result.
        """
        code = """
        b = 1
        a = b + b
        a #@
        """
        variable_a = extract_node(code)
        self.assertEqual(variable_a.inferred()[0].value, 2)

    def test_nonregr_layed_dictunpack(self) -> None:
        """Regression test for https://github.com/pylint-dev/astroid/issues/483
        Make sure multiple dictunpack references are inferable.
        """
        code = """
        base = {'data': 0}
        new = {**base, 'data': 1}
        new3 = {**base, **new}
        new3 #@
        """
        ass = extract_node(code)
        self.assertIsInstance(ass.inferred()[0], nodes.Dict)

    def test_nonregr_inference_modifying_col_offset(self) -> None:
        """Make sure inference doesn't improperly modify col_offset.

        Regression test for https://github.com/pylint-dev/pylint/issues/1839
        """

        code = """
        class F:
            def _(self):
                return type(self).f
        """
        mod = parse(code)
        cdef = mod.body[0]
        call = cdef.body[0].body[0].value.expr
        orig_offset = cdef.col_offset
        call.inferred()
        self.assertEqual(cdef.col_offset, orig_offset)

    def test_no_runtime_error_in_repeat_inference(self) -> None:
        """Stop repeat inference attempt causing a RuntimeError in Python3.7.

        See https://github.com/pylint-dev/pylint/issues/2317
        """
        code = """

        class ContextMixin:
            def get_context_data(self, **kwargs):
                return kwargs

        class DVM(ContextMixin):
            def get_context_data(self, **kwargs):
                ctx = super().get_context_data(**kwargs)
                return ctx


        class IFDVM(DVM):
            def get_context_data(self, **kwargs):
                ctx = super().get_context_data(**kwargs)
                ctx['bar'] = 'foo'
                ctx #@
                return ctx
        """
        node = extract_node(code)
        assert isinstance(node, nodes.NodeNG)
        results = node.inferred()
        assert len(results) == 2
        assert all(isinstance(result, nodes.Dict) for result in results)

    def test_name_repeat_inference(self) -> None:
        node = extract_node("print")
        context = InferenceContext()
        _ = next(node.infer(context=context))
        with pytest.raises(InferenceError):
            next(node.infer(context=context))

    def test_python25_no_relative_import(self) -> None:
        ast = resources.build_file("data/package/absimport.py")
        self.assertTrue(ast.absolute_import_activated(), True)
        inferred = next(
            test_utils.get_name_node(ast, "import_package_subpackage_module").infer()
        )
        # failed to import since absolute_import is activated
        self.assertIs(inferred, util.Uninferable)

    def test_nonregr_absolute_import(self) -> None:
        ast = resources.build_file("data/absimp/string.py", "data.absimp.string")
        self.assertTrue(ast.absolute_import_activated(), True)
        inferred = next(test_utils.get_name_node(ast, "string").infer())
        self.assertIsInstance(inferred, nodes.Module)
        self.assertEqual(inferred.name, "string")
        self.assertIn("ascii_letters", inferred.locals)

    def test_property(self) -> None:
        code = """
            from smtplib import SMTP
            class SendMailController(object):

                @property
                def smtp(self):
                    return SMTP(mailhost, port)

                @property
                def me(self):
                    return self

            my_smtp = SendMailController().smtp
            my_me = SendMailController().me
            """
        decorators = {"builtins.property"}
        ast = parse(code, __name__)
        self.assertEqual(ast["SendMailController"]["smtp"].decoratornames(), decorators)
        propinferred = list(ast.body[2].value.infer())
        self.assertEqual(len(propinferred), 1)
        propinferred = propinferred[0]
        self.assertIsInstance(propinferred, Instance)
        self.assertEqual(propinferred.name, "SMTP")
        self.assertEqual(propinferred.root().name, "smtplib")
        self.assertEqual(ast["SendMailController"]["me"].decoratornames(), decorators)
        propinferred = list(ast.body[3].value.infer())
        self.assertEqual(len(propinferred), 1)
        propinferred = propinferred[0]
        self.assertIsInstance(propinferred, Instance)
        self.assertEqual(propinferred.name, "SendMailController")
        self.assertEqual(propinferred.root().name, __name__)

    def test_im_func_unwrap(self) -> None:
        code = """
            class EnvBasedTC:
                def pactions(self):
                    pass
            pactions = EnvBasedTC.pactions.im_func
            print (pactions)

            class EnvBasedTC2:
                pactions = EnvBasedTC.pactions.im_func
                print (pactions)
            """
        ast = parse(code, __name__)
        pactions = test_utils.get_name_node(ast, "pactions")
        inferred = list(pactions.infer())
        self.assertEqual(len(inferred), 1)
        self.assertIsInstance(inferred[0], nodes.FunctionDef)
        pactions = test_utils.get_name_node(ast["EnvBasedTC2"], "pactions")
        inferred = list(pactions.infer())
        self.assertEqual(len(inferred), 1)
        self.assertIsInstance(inferred[0], nodes.FunctionDef)

    def test_augassign(self) -> None:
        code = """
            a = 1
            a += 2
            print (a)
        """
        ast = parse(code, __name__)
        inferred = list(test_utils.get_name_node(ast, "a").infer())

        self.assertEqual(len(inferred), 1)
        self.assertIsInstance(inferred[0], nodes.Const)
        self.assertEqual(inferred[0].value, 3)

    def test_nonregr_func_arg(self) -> None:
        code = """
            def foo(self, bar):
                def baz():
                    pass
                def qux():
                    return baz
                spam = bar(None, qux)
                print (spam)
            """
        ast = parse(code, __name__)
        inferred = list(test_utils.get_name_node(ast["foo"], "spam").infer())
        self.assertEqual(len(inferred), 1)
        self.assertIs(inferred[0], util.Uninferable)

    def test_nonregr_func_global(self) -> None:
        code = """
            active_application = None

            def get_active_application():
              global active_application
              return active_application

            class Application(object):
              def __init__(self):
                 global active_application
                 active_application = self

            class DataManager(object):
              def __init__(self, app=None):
                 self.app = get_active_application()
              def test(self):
                 p = self.app
                 print (p)
        """
        ast = parse(code, __name__)
        inferred = list(Instance(ast["DataManager"]).igetattr("app"))
        self.assertEqual(len(inferred), 2, inferred)  # None / Instance(Application)
        inferred = list(
            test_utils.get_name_node(ast["DataManager"]["test"], "p").infer()
        )
        self.assertEqual(len(inferred), 2, inferred)
        for node in inferred:
            if isinstance(node, Instance) and node.name == "Application":
                break
        else:
            self.fail(f"expected to find an instance of Application in {inferred}")

    def test_list_inference(self) -> None:
        code = """
            from unknown import Unknown
            A = []
            B = []

            def test():
              xyz = [
                Unknown
              ] + A + B
              return xyz

            Z = test()
        """
        ast = parse(code, __name__)
        inferred = next(ast["Z"].infer())
        self.assertIsInstance(inferred, nodes.List)
        self.assertEqual(len(inferred.elts), 1)
        self.assertIsInstance(inferred.elts[0], nodes.Unknown)

    def test__new__(self) -> None:
        code = """
            class NewTest(object):
                "doc"
                def __new__(cls, arg):
                    self = object.__new__(cls)
                    self.arg = arg
                    return self

            n = NewTest()
        """
        ast = parse(code, __name__)
        self.assertRaises(InferenceError, list, ast["NewTest"].igetattr("arg"))
        n = next(ast["n"].infer())
        inferred = list(n.igetattr("arg"))
        self.assertEqual(len(inferred), 1, inferred)

    def test__new__bound_methods(self) -> None:
        node = extract_node(
            """
        class cls(object): pass
        cls().__new__(cls) #@
        """
        )
        inferred = next(node.infer())
        self.assertIsInstance(inferred, Instance)
        self.assertEqual(inferred._proxied, node.root()["cls"])

    def test_two_parents_from_same_module(self) -> None:
        code = """
            from data import nonregr
            class Xxx(nonregr.Aaa, nonregr.Ccc):
                "doc"
        """
        ast = parse(code, __name__)
        parents = list(ast["Xxx"].ancestors())
        self.assertEqual(len(parents), 3, parents)  # Aaa, Ccc, object

    def test_pluggable_inference(self) -> None:
        code = """
            from collections import namedtuple
            A = namedtuple('A', ['a', 'b'])
            B = namedtuple('B', 'a b')
        """
        ast = parse(code, __name__)
        aclass = ast["A"].inferred()[0]
        self.assertIsInstance(aclass, nodes.ClassDef)
        self.assertIn("a", aclass.instance_attrs)
        self.assertIn("b", aclass.instance_attrs)
        bclass = ast["B"].inferred()[0]
        self.assertIsInstance(bclass, nodes.ClassDef)
        self.assertIn("a", bclass.instance_attrs)
        self.assertIn("b", bclass.instance_attrs)

    def test_infer_arguments(self) -> None:
        code = """
            class A(object):
                def first(self, arg1, arg2):
                    return arg1
                @classmethod
                def method(cls, arg1, arg2):
                    return arg2
                @classmethod
                def empty(cls):
                    return 2
                @staticmethod
                def static(arg1, arg2):
                    return arg1
                def empty_method(self):
                    return []
            x = A().first(1, [])
            y = A.method(1, [])
            z = A.static(1, [])
            empty = A.empty()
            empty_list = A().empty_method()
        """
        ast = parse(code, __name__)
        int_node = ast["x"].inferred()[0]
        self.assertIsInstance(int_node, nodes.Const)
        self.assertEqual(int_node.value, 1)
        list_node = ast["y"].inferred()[0]
        self.assertIsInstance(list_node, nodes.List)
        int_node = ast["z"].inferred()[0]
        self.assertIsInstance(int_node, nodes.Const)
        self.assertEqual(int_node.value, 1)
        empty = ast["empty"].inferred()[0]
        self.assertIsInstance(empty, nodes.Const)
        self.assertEqual(empty.value, 2)
        empty_list = ast["empty_list"].inferred()[0]
        self.assertIsInstance(empty_list, nodes.List)

    def test_infer_variable_arguments(self) -> None:
        code = """
            def test(*args, **kwargs):
                vararg = args
                kwarg = kwargs
        """
        ast = parse(code, __name__)
        func = ast["test"]
        vararg = func.body[0].value
        kwarg = func.body[1].value

        kwarg_inferred = kwarg.inferred()[0]
        self.assertIsInstance(kwarg_inferred, nodes.Dict)
        self.assertIs(kwarg_inferred.parent, func.args)

        vararg_inferred = vararg.inferred()[0]
        self.assertIsInstance(vararg_inferred, nodes.Tuple)
        self.assertIs(vararg_inferred.parent, func.args)

    def test_infer_nested(self) -> None:
        code = """
            def nested():
                from threading import Thread

                class NestedThread(Thread):
                    def __init__(self):
                        Thread.__init__(self)
        """
        # Test that inferring Thread.__init__ looks up in
        # the nested scope.
        ast = parse(code, __name__)
        callfunc = next(ast.nodes_of_class(nodes.Call))
        func = callfunc.func
        inferred = func.inferred()[0]
        self.assertIsInstance(inferred, UnboundMethod)

    def test_instance_binary_operations(self) -> None:
        code = """
            class A(object):
                def __mul__(self, other):
                    return 42
            a = A()
            b = A()
            sub = a - b
            mul = a * b
        """
        ast = parse(code, __name__)
        sub = ast["sub"].inferred()[0]
        mul = ast["mul"].inferred()[0]
        self.assertIs(sub, util.Uninferable)
        self.assertIsInstance(mul, nodes.Const)
        self.assertEqual(mul.value, 42)

    def test_instance_binary_operations_parent(self) -> None:
        code = """
            class A(object):
                def __mul__(self, other):
                    return 42
            class B(A):
                pass
            a = B()
            b = B()
            sub = a - b
            mul = a * b
        """
        ast = parse(code, __name__)
        sub = ast["sub"].inferred()[0]
        mul = ast["mul"].inferred()[0]
        self.assertIs(sub, util.Uninferable)
        self.assertIsInstance(mul, nodes.Const)
        self.assertEqual(mul.value, 42)

    def test_instance_binary_operations_multiple_methods(self) -> None:
        code = """
            class A(object):
                def __mul__(self, other):
                    return 42
            class B(A):
                def __mul__(self, other):
                    return [42]
            a = B()
            b = B()
            sub = a - b
            mul = a * b
        """
        ast = parse(code, __name__)
        sub = ast["sub"].inferred()[0]
        mul = ast["mul"].inferred()[0]
        self.assertIs(sub, util.Uninferable)
        self.assertIsInstance(mul, nodes.List)
        self.assertIsInstance(mul.elts[0], nodes.Const)
        self.assertEqual(mul.elts[0].value, 42)

    def test_infer_call_result_crash(self) -> None:
        code = """
            class A(object):
                def __mul__(self, other):
                    return type.__new__()

            a = A()
            b = A()
            c = a * b
        """
        ast = parse(code, __name__)
        node = ast["c"]
        assert isinstance(node, nodes.NodeNG)
        self.assertEqual(node.inferred(), [util.Uninferable])

    def test_infer_empty_nodes(self) -> None:
        # Should not crash when trying to infer EmptyNodes.
        node = nodes.EmptyNode()
        assert isinstance(node, nodes.NodeNG)
        self.assertEqual(node.inferred(), [util.Uninferable])

    def test_infinite_loop_for_decorators(self) -> None:
        # Issue https://bitbucket.org/logilab/astroid/issue/50
        # A decorator that returns itself leads to an infinite loop.
        code = """
            def decorator():
                def wrapper():
                    return decorator()
                return wrapper

            @decorator()
            def do_a_thing():
                pass
        """
        ast = parse(code, __name__)
        node = ast["do_a_thing"]
        self.assertEqual(node.type, "function")

    def test_no_infinite_ancestor_loop(self) -> None:
        klass = extract_node(
            """
            import datetime

            def method(self):
                datetime.datetime = something()

            class something(datetime.datetime):  #@
                pass
        """
        )
        ancestors = [base.name for base in klass.ancestors()]
        expected_subset = ["datetime", "date"]
        self.assertEqual(expected_subset, ancestors[:2])

    def test_stop_iteration_leak(self) -> None:
        code = """
            class Test:
                def __init__(self):
                    self.config = {0: self.config[0]}
                    self.config[0].test() #@
        """
        ast = extract_node(code, __name__)
        expr = ast.func.expr
        self.assertIs(next(expr.infer()), util.Uninferable)

    def test_tuple_builtin_inference(self) -> None:
        code = """
        var = (1, 2)
        tuple() #@
        tuple([1]) #@
        tuple({2}) #@
        tuple("abc") #@
        tuple({1: 2}) #@
        tuple(var) #@
        tuple(tuple([1])) #@
        tuple(frozenset((1, 2))) #@

        tuple(None) #@
        tuple(1) #@
        tuple(1, 2) #@
        """
        ast = extract_node(code, __name__)

        self.assertInferTuple(ast[0], [])
        self.assertInferTuple(ast[1], [1])
        self.assertInferTuple(ast[2], [2])
        self.assertInferTuple(ast[3], ["a", "b", "c"])
        self.assertInferTuple(ast[4], [1])
        self.assertInferTuple(ast[5], [1, 2])
        self.assertInferTuple(ast[6], [1])
        self.assertInferTuple(ast[7], [1, 2])

        for node in ast[8:]:
            inferred = next(node.infer())
            self.assertIsInstance(inferred, Instance)
            self.assertEqual(inferred.qname(), "builtins.tuple")

    def test_starred_in_tuple_literal(self) -> None:
        code = """
        var = (1, 2, 3)
        bar = (5, 6, 7)
        foo = [999, 1000, 1001]
        (0, *var) #@
        (0, *var, 4) #@
        (0, *var, 4, *bar) #@
        (0, *var, 4, *(*bar, 8)) #@
        (0, *var, 4, *(*bar, *foo)) #@
        """
        ast = extract_node(code, __name__)
        self.assertInferTuple(ast[0], [0, 1, 2, 3])
        self.assertInferTuple(ast[1], [0, 1, 2, 3, 4])
        self.assertInferTuple(ast[2], [0, 1, 2, 3, 4, 5, 6, 7])
        self.assertInferTuple(ast[3], [0, 1, 2, 3, 4, 5, 6, 7, 8])
        self.assertInferTuple(ast[4], [0, 1, 2, 3, 4, 5, 6, 7, 999, 1000, 1001])

    def test_starred_in_list_literal(self) -> None:
        code = """
        var = (1, 2, 3)
        bar = (5, 6, 7)
        foo = [999, 1000, 1001]
        [0, *var] #@
        [0, *var, 4] #@
        [0, *var, 4, *bar] #@
        [0, *var, 4, *[*bar, 8]] #@
        [0, *var, 4, *[*bar, *foo]] #@
        """
        ast = extract_node(code, __name__)
        self.assertInferList(ast[0], [0, 1, 2, 3])
        self.assertInferList(ast[1], [0, 1, 2, 3, 4])
        self.assertInferList(ast[2], [0, 1, 2, 3, 4, 5, 6, 7])
        self.assertInferList(ast[3], [0, 1, 2, 3, 4, 5, 6, 7, 8])
        self.assertInferList(ast[4], [0, 1, 2, 3, 4, 5, 6, 7, 999, 1000, 1001])

    def test_starred_in_set_literal(self) -> None:
        code = """
        var = (1, 2, 3)
        bar = (5, 6, 7)
        foo = [999, 1000, 1001]
        {0, *var} #@
        {0, *var, 4} #@
        {0, *var, 4, *bar} #@
        {0, *var, 4, *{*bar, 8}} #@
        {0, *var, 4, *{*bar, *foo}} #@
        """
        ast = extract_node(code, __name__)
        self.assertInferSet(ast[0], [0, 1, 2, 3])
        self.assertInferSet(ast[1], [0, 1, 2, 3, 4])
        self.assertInferSet(ast[2], [0, 1, 2, 3, 4, 5, 6, 7])
        self.assertInferSet(ast[3], [0, 1, 2, 3, 4, 5, 6, 7, 8])
        self.assertInferSet(ast[4], [0, 1, 2, 3, 4, 5, 6, 7, 999, 1000, 1001])

    def test_starred_in_literals_inference_issues(self) -> None:
        code = """
        {0, *var} #@
        {0, *var, 4} #@
        {0, *var, 4, *bar} #@
        {0, *var, 4, *{*bar, 8}} #@
        {0, *var, 4, *{*bar, *foo}} #@
        """
        ast = extract_node(code, __name__)
        for node in ast:
            with self.assertRaises(InferenceError):
                next(node.infer())

    def test_starred_in_mapping_literal(self) -> None:
        code = """
        var = {1: 'b', 2: 'c'}
        bar = {4: 'e', 5: 'f'}
        {0: 'a', **var} #@
        {0: 'a', **var, 3: 'd'} #@
        {0: 'a', **var, 3: 'd', **{**bar, 6: 'g'}} #@
        """
        ast = extract_node(code, __name__)
        self.assertInferDict(ast[0], {0: "a", 1: "b", 2: "c"})
        self.assertInferDict(ast[1], {0: "a", 1: "b", 2: "c", 3: "d"})
        self.assertInferDict(
            ast[2], {0: "a", 1: "b", 2: "c", 3: "d", 4: "e", 5: "f", 6: "g"}
        )

    def test_starred_in_mapping_literal_no_inference_possible(self) -> None:
        node = extract_node(
            """
        from unknown import unknown

        def test(a):
           return a + 1

        def func():
            a = {unknown: 'a'}
            return {0: 1, **a}

        test(**func())
        """
        )
        self.assertEqual(next(node.infer()), util.Uninferable)

    def test_starred_in_mapping_inference_issues(self) -> None:
        code = """
        {0: 'a', **var} #@
        {0: 'a', **var, 3: 'd'} #@
        {0: 'a', **var, 3: 'd', **{**bar, 6: 'g'}} #@
        """
        ast = extract_node(code, __name__)
        for node in ast:
            with self.assertRaises(InferenceError):
                next(node.infer())

    def test_starred_in_mapping_literal_non_const_keys_values(self) -> None:
        code = """
        a, b, c, d, e, f, g, h, i, j = "ABCDEFGHIJ"
        var = {c: d, e: f}
        bar = {i: j}
        {a: b, **var} #@
        {a: b, **var, **{g: h, **bar}} #@
        """
        ast = extract_node(code, __name__)
        self.assertInferDict(ast[0], {"A": "B", "C": "D", "E": "F"})
        self.assertInferDict(ast[1], {"A": "B", "C": "D", "E": "F", "G": "H", "I": "J"})

    def test_frozenset_builtin_inference(self) -> None:
        code = """
        var = (1, 2)
        frozenset() #@
        frozenset([1, 2, 1]) #@
        frozenset({2, 3, 1}) #@
        frozenset("abcab") #@
        frozenset({1: 2}) #@
        frozenset(var) #@
        frozenset(tuple([1])) #@

        frozenset(set(tuple([4, 5, set([2])]))) #@
        frozenset(None) #@
        frozenset(1) #@
        frozenset(1, 2) #@
        """
        ast = extract_node(code, __name__)

        self.assertInferFrozenSet(ast[0], [])
        self.assertInferFrozenSet(ast[1], [1, 2])
        self.assertInferFrozenSet(ast[2], [1, 2, 3])
        self.assertInferFrozenSet(ast[3], ["a", "b", "c"])
        self.assertInferFrozenSet(ast[4], [1])
        self.assertInferFrozenSet(ast[5], [1, 2])
        self.assertInferFrozenSet(ast[6], [1])

        for node in ast[7:]:
            inferred = next(node.infer())
            self.assertIsInstance(inferred, Instance)
            self.assertEqual(inferred.qname(), "builtins.frozenset")

    def test_set_builtin_inference(self) -> None:
        code = """
        var = (1, 2)
        set() #@
        set([1, 2, 1]) #@
        set({2, 3, 1}) #@
        set("abcab") #@
        set({1: 2}) #@
        set(var) #@
        set(tuple([1])) #@

        set(set(tuple([4, 5, set([2])]))) #@
        set(None) #@
        set(1) #@
        set(1, 2) #@
        """
        ast = extract_node(code, __name__)

        self.assertInferSet(ast[0], [])
        self.assertInferSet(ast[1], [1, 2])
        self.assertInferSet(ast[2], [1, 2, 3])
        self.assertInferSet(ast[3], ["a", "b", "c"])
        self.assertInferSet(ast[4], [1])
        self.assertInferSet(ast[5], [1, 2])
        self.assertInferSet(ast[6], [1])

        for node in ast[7:]:
            inferred = next(node.infer())
            self.assertIsInstance(inferred, Instance)
            self.assertEqual(inferred.qname(), "builtins.set")

    def test_list_builtin_inference(self) -> None:
        code = """
        var = (1, 2)
        list() #@
        list([1, 2, 1]) #@
        list({2, 3, 1}) #@
        list("abcab") #@
        list({1: 2}) #@
        list(var) #@
        list(tuple([1])) #@

        list(list(tuple([4, 5, list([2])]))) #@
        list(None) #@
        list(1) #@
        list(1, 2) #@
        """
        ast = extract_node(code, __name__)
        self.assertInferList(ast[0], [])
        self.assertInferList(ast[1], [1, 1, 2])
        self.assertInferList(ast[2], [1, 2, 3])
        self.assertInferList(ast[3], ["a", "a", "b", "b", "c"])
        self.assertInferList(ast[4], [1])
        self.assertInferList(ast[5], [1, 2])
        self.assertInferList(ast[6], [1])

        for node in ast[7:]:
            inferred = next(node.infer())
            self.assertIsInstance(inferred, Instance)
            self.assertEqual(inferred.qname(), "builtins.list")

    def test_conversion_of_dict_methods(self) -> None:
        ast_nodes = extract_node(
            """
        list({1:2, 2:3}.values()) #@
        list({1:2, 2:3}.keys()) #@
        tuple({1:2, 2:3}.values()) #@
        tuple({1:2, 3:4}.keys()) #@
        set({1:2, 2:4}.keys()) #@
        """
        )
        assert isinstance(ast_nodes, list)
        self.assertInferList(ast_nodes[0], [2, 3])
        self.assertInferList(ast_nodes[1], [1, 2])
        self.assertInferTuple(ast_nodes[2], [2, 3])
        self.assertInferTuple(ast_nodes[3], [1, 3])
        self.assertInferSet(ast_nodes[4], [1, 2])

    def test_builtin_inference_py3k(self) -> None:
        code = """
        list(b"abc") #@
        tuple(b"abc") #@
        set(b"abc") #@
        """
        ast = extract_node(code, __name__)
        self.assertInferList(ast[0], [97, 98, 99])
        self.assertInferTuple(ast[1], [97, 98, 99])
        self.assertInferSet(ast[2], [97, 98, 99])

    def test_dict_inference(self) -> None:
        code = """
        dict() #@
        dict(a=1, b=2, c=3) #@
        dict([(1, 2), (2, 3)]) #@
        dict([[1, 2], [2, 3]]) #@
        dict([(1, 2), [2, 3]]) #@
        dict([('a', 2)], b=2, c=3) #@
        dict({1: 2}) #@
        dict({'c': 2}, a=4, b=5) #@
        def func():
            return dict(a=1, b=2)
        func() #@
        var = {'x': 2, 'y': 3}
        dict(var, a=1, b=2) #@

        dict([1, 2, 3]) #@
        dict([(1, 2), (1, 2, 3)]) #@
        dict({1: 2}, {1: 2}) #@
        dict({1: 2}, (1, 2)) #@
        dict({1: 2}, (1, 2), a=4) #@
        dict([(1, 2), ([4, 5], 2)]) #@
        dict([None,  None]) #@

        def using_unknown_kwargs(**kwargs):
            return dict(**kwargs)
        using_unknown_kwargs(a=1, b=2) #@
        """
        ast = extract_node(code, __name__)
        self.assertInferDict(ast[0], {})
        self.assertInferDict(ast[1], {"a": 1, "b": 2, "c": 3})
        for i in range(2, 5):
            self.assertInferDict(ast[i], {1: 2, 2: 3})
        self.assertInferDict(ast[5], {"a": 2, "b": 2, "c": 3})
        self.assertInferDict(ast[6], {1: 2})
        self.assertInferDict(ast[7], {"c": 2, "a": 4, "b": 5})
        self.assertInferDict(ast[8], {"a": 1, "b": 2})
        self.assertInferDict(ast[9], {"x": 2, "y": 3, "a": 1, "b": 2})

        for node in ast[10:]:
            inferred = next(node.infer())
            self.assertIsInstance(inferred, Instance)
            self.assertEqual(inferred.qname(), "builtins.dict")

    def test_dict_inference_kwargs(self) -> None:
        ast_node = extract_node("""dict(a=1, b=2, **{'c': 3})""")
        self.assertInferDict(ast_node, {"a": 1, "b": 2, "c": 3})

    def test_dict_inference_for_multiple_starred(self) -> None:
        pairs = [
            ('dict(a=1, **{"b": 2}, **{"c":3})', {"a": 1, "b": 2, "c": 3}),
            ('dict(a=1, **{"b": 2}, d=4, **{"c":3})', {"a": 1, "b": 2, "c": 3, "d": 4}),
            ('dict({"a":1}, b=2, **{"c":3})', {"a": 1, "b": 2, "c": 3}),
        ]
        for code, expected_value in pairs:
            node = extract_node(code)
            self.assertInferDict(node, expected_value)

    def test_dict_inference_unpack_repeated_key(self) -> None:
        """Make sure astroid does not infer repeated keys in a dictionary.

        Regression test for https://github.com/pylint-dev/pylint/issues/1843
        """
        code = """
        base = {'data': 0}
        new = {**base, 'data': 1} #@
        new2 = {'data': 1, **base} #@ # Make sure overwrite works
        a = 'd' + 'ata'
        b3 = {**base, a: 3} #@  Make sure keys are properly inferred
        b4 = {a: 3, **base} #@
        """
        ast = extract_node(code)
        final_values = ("{'data': 1}", "{'data': 0}", "{'data': 3}", "{'data': 0}")
        for node, final_value in zip(ast, final_values):
            assert node.targets[0].inferred()[0].as_string() == final_value

    def test_dict_invalid_args(self) -> None:
        invalid_values = ["dict(*1)", "dict(**lala)", "dict(**[])"]
        for invalid in invalid_values:
            ast_node = extract_node(invalid)
            inferred = next(ast_node.infer())
            self.assertIsInstance(inferred, Instance)
            self.assertEqual(inferred.qname(), "builtins.dict")

    def test_copy_method_inference(self) -> None:
        code = """
        a_dict = {"b": 1, "c": 2}
        b_dict = a_dict.copy()
        b_dict #@

        a_list = [1, 2, 3]
        b_list = a_list.copy()
        b_list #@

        a_set = set([1, 2, 3])
        b_set = a_set.copy()
        b_set #@

        a_frozenset = frozenset([1, 2, 3])
        b_frozenset = a_frozenset.copy()
        b_frozenset #@

        a_unknown = unknown()
        b_unknown = a_unknown.copy()
        b_unknown #@
        """
        ast = extract_node(code, __name__)
        self.assertInferDict(ast[0], {"b": 1, "c": 2})
        self.assertInferList(ast[1], [1, 2, 3])
        self.assertInferSet(ast[2], [1, 2, 3])
        self.assertInferFrozenSet(ast[3], [1, 2, 3])

        inferred_unknown = next(ast[4].infer())
        assert inferred_unknown == util.Uninferable

    def test_str_methods(self) -> None:
        code = """
        ' '.decode() #@
        ' '.join('abcd') #@
        ' '.replace('a', 'b') #@
        ' '.capitalize() #@
        ' '.title() #@
        ' '.lower() #@
        ' '.upper() #@
        ' '.swapcase() #@
        ' '.strip() #@
        ' '.rstrip() #@
        ' '.lstrip() #@
        ' '.rjust() #@
        ' '.ljust() #@
        ' '.center() #@

        ' '.index() #@
        ' '.find() #@
        ' '.count() #@

        ' '.format('a') #@
        """
        ast = extract_node(code, __name__)
        self.assertInferConst(ast[0], "")
        for i in range(1, 14):
            self.assertInferConst(ast[i], "")
        for i in range(14, 17):
            self.assertInferConst(ast[i], 0)
        self.assertInferConst(ast[17], " ")

    def test_unicode_methods(self) -> None:
        code = """
        u' '.decode() #@
        u' '.join('abcd') #@
        u' '.replace('a', 'b') #@
        u' '.capitalize() #@
        u' '.title() #@
        u' '.lower() #@
        u' '.upper() #@
        u' '.swapcase() #@
        u' '.strip() #@
        u' '.rstrip() #@
        u' '.lstrip() #@
        u' '.rjust() #@
        u' '.ljust() #@
        u' '.center() #@

        u' '.index() #@
        u' '.find() #@
        u' '.count() #@

        u' '.format('a') #@
        """
        ast = extract_node(code, __name__)
        self.assertInferConst(ast[0], "")
        for i in range(1, 14):
            self.assertInferConst(ast[i], "")
        for i in range(14, 17):
            self.assertInferConst(ast[i], 0)
        self.assertInferConst(ast[17], " ")

    def test_scope_lookup_same_attributes(self) -> None:
        code = """
        import collections
        class Second(collections.Counter):
            def collections(self):
                return "second"

        """
        ast = parse(code, __name__)
        bases = ast["Second"].bases[0]
        inferred = next(bases.infer())
        self.assertTrue(inferred)
        self.assertIsInstance(inferred, nodes.ClassDef)
        self.assertEqual(inferred.qname(), "collections.Counter")

    def test_inferring_with_statement_failures(self) -> None:
        module = parse(
            """
        class NoEnter(object):
            pass
        class NoMethod(object):
            __enter__ = None
        class NoElts(object):
            def __enter__(self):
                return 42

        with NoEnter() as no_enter:
            pass
        with NoMethod() as no_method:
            pass
        with NoElts() as (no_elts, no_elts1):
            pass
        """
        )
        self.assertRaises(InferenceError, next, module["no_enter"].infer())
        self.assertRaises(InferenceError, next, module["no_method"].infer())
        self.assertRaises(InferenceError, next, module["no_elts"].infer())

    def test_inferring_with_statement(self) -> None:
        module = parse(
            """
        class SelfContext(object):
            def __enter__(self):
                return self

        class OtherContext(object):
            def __enter__(self):
                return SelfContext()

        class MultipleReturns(object):
            def __enter__(self):
                return SelfContext(), OtherContext()

        class MultipleReturns2(object):
            def __enter__(self):
                return [1, [2, 3]]

        with SelfContext() as self_context:
            pass
        with OtherContext() as other_context:
            pass
        with MultipleReturns(), OtherContext() as multiple_with:
            pass
        with MultipleReturns2() as (stdout, (stderr, stdin)):
            pass
        """
        )
        self_context = module["self_context"]
        inferred = next(self_context.infer())
        self.assertIsInstance(inferred, Instance)
        self.assertEqual(inferred.name, "SelfContext")

        other_context = module["other_context"]
        inferred = next(other_context.infer())
        self.assertIsInstance(inferred, Instance)
        self.assertEqual(inferred.name, "SelfContext")

        multiple_with = module["multiple_with"]
        inferred = next(multiple_with.infer())
        self.assertIsInstance(inferred, Instance)
        self.assertEqual(inferred.name, "SelfContext")

        stdout = module["stdout"]
        inferred = next(stdout.infer())
        self.assertIsInstance(inferred, nodes.Const)
        self.assertEqual(inferred.value, 1)
        stderr = module["stderr"]
        inferred = next(stderr.infer())
        self.assertIsInstance(inferred, nodes.Const)
        self.assertEqual(inferred.value, 2)

    def test_inferring_with_contextlib_contextmanager(self) -> None:
        module = parse(
            """
        import contextlib
        from contextlib import contextmanager

        @contextlib.contextmanager
        def manager_none():
            try:
                yield
            finally:
                pass

        @contextlib.contextmanager
        def manager_something():
            try:
                yield 42
                yield 24 # This should be ignored.
            finally:
                pass

        @contextmanager
        def manager_multiple():
            with manager_none() as foo:
                with manager_something() as bar:
                    yield foo, bar

        with manager_none() as none:
            pass
        with manager_something() as something:
            pass
        with manager_multiple() as (first, second):
            pass
        """
        )
        none = module["none"]
        inferred = next(none.infer())
        self.assertIsInstance(inferred, nodes.Const)
        self.assertIsNone(inferred.value)

        something = module["something"]
        inferred = something.inferred()
        self.assertEqual(len(inferred), 1)
        inferred = inferred[0]
        self.assertIsInstance(inferred, nodes.Const)
        self.assertEqual(inferred.value, 42)

        first, second = module["first"], module["second"]
        first = next(first.infer())
        second = next(second.infer())
        self.assertIsInstance(first, nodes.Const)
        self.assertIsNone(first.value)
        self.assertIsInstance(second, nodes.Const)
        self.assertEqual(second.value, 42)

    def test_inferring_context_manager_skip_index_error(self) -> None:
        # Raise an InferenceError when having multiple 'as' bindings
        # from a context manager, but its result doesn't have those
        # indices. This is the case of contextlib.nested, where the
        # result is a list, which is mutated later on, so it's
        # undetected by astroid.
        module = parse(
            """
        class Manager(object):
            def __enter__(self):
                return []
        with Manager() as (a, b, c):
            pass
        """
        )
        self.assertRaises(InferenceError, next, module["a"].infer())

    def test_inferring_context_manager_unpacking_inference_error(self) -> None:
        # https://github.com/pylint-dev/pylint/issues/1463
        module = parse(
            """
        import contextlib

        @contextlib.contextmanager
        def _select_source(a=None):
            with _select_source() as result:
                yield result

        result = _select_source()
        with result as (a, b, c):
            pass
        """
        )
        self.assertRaises(InferenceError, next, module["a"].infer())

    def test_inferring_with_contextlib_contextmanager_failures(self) -> None:
        module = parse(
            """
        from contextlib import contextmanager

        def no_decorators_mgr():
            yield
        @no_decorators_mgr
        def other_decorators_mgr():
            yield
        @contextmanager
        def no_yield_mgr():
            pass

        with no_decorators_mgr() as no_decorators:
            pass
        with other_decorators_mgr() as other_decorators:
            pass
        with no_yield_mgr() as no_yield:
            pass
        """
        )
        self.assertRaises(InferenceError, next, module["no_decorators"].infer())
        self.assertRaises(InferenceError, next, module["other_decorators"].infer())
        self.assertRaises(InferenceError, next, module["no_yield"].infer())

    def test_nested_contextmanager(self) -> None:
        """Make sure contextmanager works with nested functions.

        Previously contextmanager would retrieve
        the first yield instead of the yield in the
        proper scope

        Fixes https://github.com/pylint-dev/pylint/issues/1746
        """
        code = """
        from contextlib import contextmanager

        @contextmanager
        def outer():
            @contextmanager
            def inner():
                yield 2
            yield inner

        with outer() as ctx:
            ctx #@
            with ctx() as val:
                val #@
        """
        context_node, value_node = extract_node(code)
        value = next(value_node.infer())
        context = next(context_node.infer())
        assert isinstance(context, nodes.FunctionDef)
        assert isinstance(value, nodes.Const)

    def test_unary_op_leaks_stop_iteration(self) -> None:
        node = extract_node("+[] #@")
        self.assertEqual(util.Uninferable, next(node.infer()))

    def test_unary_operands(self) -> None:
        ast_nodes = extract_node(
            """
        import os
        def func(): pass
        from missing import missing
        class GoodInstance(object):
            def __pos__(self):
                return 42
            def __neg__(self):
                return +self - 41
            def __invert__(self):
                return 42
        class BadInstance(object):
            def __pos__(self):
                return lala
            def __neg__(self):
                return missing
        class LambdaInstance(object):
            __pos__ = lambda self: self.lala
            __neg__ = lambda self: self.lala + 1
            @property
            def lala(self): return 24
        class InstanceWithAttr(object):
            def __init__(self):
                self.x = 42
            def __pos__(self):
                return self.x
            def __neg__(self):
                return +self - 41
            def __invert__(self):
                return self.x + 1
        instance = GoodInstance()
        lambda_instance = LambdaInstance()
        instance_with_attr = InstanceWithAttr()
        +instance #@
        -instance #@
        ~instance #@
        --instance #@
        +lambda_instance #@
        -lambda_instance #@
        +instance_with_attr #@
        -instance_with_attr #@
        ~instance_with_attr #@

        bad_instance = BadInstance()
        +bad_instance #@
        -bad_instance #@
        ~bad_instance #@

        # These should be TypeErrors.
        ~BadInstance #@
        ~os #@
        -func #@
        +BadInstance #@
        """
        )
        expected = [42, 1, 42, -1, 24, 25, 42, 1, 43]
        for node, value in zip(ast_nodes[:9], expected):
            inferred = next(node.infer())
            self.assertIsInstance(inferred, nodes.Const)
            self.assertEqual(inferred.value, value)

        for bad_node in ast_nodes[9:]:
            inferred = next(bad_node.infer())
            self.assertEqual(inferred, util.Uninferable)

    def test_unary_op_instance_method_not_callable(self) -> None:
        ast_node = extract_node(
            """
        class A:
            __pos__ = (i for i in range(10))
        +A() #@
        """
        )
        self.assertRaises(InferenceError, next, ast_node.infer())

    def test_binary_op_type_errors(self) -> None:
        ast_nodes = extract_node(
            """
        import collections
        1 + "a" #@
        1 - [] #@
        1 * {} #@
        1 / collections #@
        1 ** (lambda x: x) #@
        {} * {} #@
        {} - {} #@
        {} >> {} #@
        [] + () #@
        () + [] #@
        [] * 2.0 #@
        () * 2.0 #@
        2.0 >> 2.0 #@
        class A(object): pass
        class B(object): pass
        A() + B() #@
        class A1(object):
            def __add__(self, other): return NotImplemented
        A1() + A1() #@
        class A(object):
            def __add__(self, other): return NotImplemented
        class B(object):
            def __radd__(self, other): return NotImplemented
        A() + B() #@
        class Parent(object):
            pass
        class Child(Parent):
            def __add__(self, other): return NotImplemented
        Child() + Parent() #@
        class A(object):
            def __add__(self, other): return NotImplemented
        class B(A):
            def __radd__(self, other):
                 return NotImplemented
        A() + B() #@
        # Augmented
        f = 1
        f+=A() #@
        x = 1
        x+=[] #@
        """
        )
        msg = "unsupported operand type(s) for {op}: {lhs!r} and {rhs!r}"
        expected = [
            msg.format(op="+", lhs="int", rhs="str"),
            msg.format(op="-", lhs="int", rhs="list"),
            msg.format(op="*", lhs="int", rhs="dict"),
            msg.format(op="/", lhs="int", rhs="module"),
            msg.format(op="**", lhs="int", rhs="function"),
            msg.format(op="*", lhs="dict", rhs="dict"),
            msg.format(op="-", lhs="dict", rhs="dict"),
            msg.format(op=">>", lhs="dict", rhs="dict"),
            msg.format(op="+", lhs="list", rhs="tuple"),
            msg.format(op="+", lhs="tuple", rhs="list"),
            msg.format(op="*", lhs="list", rhs="float"),
            msg.format(op="*", lhs="tuple", rhs="float"),
            msg.format(op=">>", lhs="float", rhs="float"),
            msg.format(op="+", lhs="A", rhs="B"),
            msg.format(op="+", lhs="A1", rhs="A1"),
            msg.format(op="+", lhs="A", rhs="B"),
            msg.format(op="+", lhs="Child", rhs="Parent"),
            msg.format(op="+", lhs="A", rhs="B"),
            msg.format(op="+=", lhs="int", rhs="A"),
            msg.format(op="+=", lhs="int", rhs="list"),
        ]

        for node, expected_value in zip(ast_nodes, expected):
            errors = node.type_errors()
            self.assertEqual(len(errors), 1)
            error = errors[0]
            self.assertEqual(str(error), expected_value)

    def test_binary_type_errors_partially_uninferable(self) -> None:
        def patched_infer_binop(context):
            return iter([util.BadBinaryOperationMessage(None, None, None), Uninferable])

        binary_op_node = extract_node("0 + 0")
        binary_op_node._infer_binop = patched_infer_binop
        errors = binary_op_node.type_errors()
        self.assertEqual(errors, [])

    def test_unary_type_errors(self) -> None:
        ast_nodes = extract_node(
            """
        import collections
        ~[] #@
        ~() #@
        ~dict() #@
        ~{} #@
        ~set() #@
        -set() #@
        -"" #@
        ~"" #@
        +"" #@
        class A(object): pass
        ~(lambda: None) #@
        ~A #@
        ~A() #@
        ~collections #@
        ~2.0 #@
        """
        )
        msg = "bad operand type for unary {op}: {type}"
        expected = [
            msg.format(op="~", type="list"),
            msg.format(op="~", type="tuple"),
            msg.format(op="~", type="dict"),
            msg.format(op="~", type="dict"),
            msg.format(op="~", type="set"),
            msg.format(op="-", type="set"),
            msg.format(op="-", type="str"),
            msg.format(op="~", type="str"),
            msg.format(op="+", type="str"),
            msg.format(op="~", type="<lambda>"),
            msg.format(op="~", type="A"),
            msg.format(op="~", type="A"),
            msg.format(op="~", type="collections"),
            msg.format(op="~", type="float"),
        ]
        for node, expected_value in zip(ast_nodes, expected):
            errors = node.type_errors()
            self.assertEqual(len(errors), 1)
            error = errors[0]
            self.assertEqual(str(error), expected_value)

    def test_unary_empty_type_errors(self) -> None:
        # These aren't supported right now
        ast_nodes = extract_node(
            """
        ~(2 and []) #@
        -(0 or {}) #@
        """
        )
        expected = [
            "bad operand type for unary ~: list",
            "bad operand type for unary -: dict",
        ]
        for node, expected_value in zip(ast_nodes, expected):
            errors = node.type_errors()
            self.assertEqual(len(errors), 1, (expected, node))
            self.assertEqual(str(errors[0]), expected_value)

    def test_unary_type_errors_for_non_instance_objects(self) -> None:
        node = extract_node("~slice(1, 2, 3)")
        errors = node.type_errors()
        self.assertEqual(len(errors), 1)
        self.assertEqual(str(errors[0]), "bad operand type for unary ~: slice")

    def test_unary_type_errors_partially_uninferable(self) -> None:
        def patched_infer_unary_op(context):
            return iter([util.BadUnaryOperationMessage(None, None, "msg"), Uninferable])

        unary_op_node = extract_node("~0")
        unary_op_node._infer_unaryop = patched_infer_unary_op
        errors = unary_op_node.type_errors()
        self.assertEqual(errors, [])

    def test_bool_value_recursive(self) -> None:
        pairs = [
            ("{}", False),
            ("{1:2}", True),
            ("()", False),
            ("(1, 2)", True),
            ("[]", False),
            ("[1,2]", True),
            ("frozenset()", False),
            ("frozenset((1, 2))", True),
        ]
        for code, expected in pairs:
            node = extract_node(code)
            inferred = next(node.infer())
            self.assertEqual(inferred.bool_value(), expected)

    def test_genexpr_bool_value(self) -> None:
        node = extract_node("""(x for x in range(10))""")
        self.assertTrue(node.bool_value())

    def test_name_bool_value(self) -> None:
        node = extract_node(
            """
        x = 42
        y = x
        y
        """
        )
        self.assertIs(node.bool_value(), util.Uninferable)

    def test_bool_value(self) -> None:
        # Verify the truth value of nodes.
        module = parse(
            """
        import collections
        collections_module = collections
        def function(): pass
        class Class(object):
            def method(self): pass
        dict_comp = {x:y for (x, y) in ((1, 2), (2, 3))}
        set_comp = {x for x in range(10)}
        list_comp = [x for x in range(10)]
        lambda_func = lambda: None
        unbound_method = Class.method
        instance = Class()
        bound_method = instance.method
        def generator_func():
             yield
        def true_value():
             return True
        generator = generator_func()
        bin_op = 1 + 2
        bool_op = x and y
        callfunc = test()
        good_callfunc = true_value()
        compare = 2 < 3
        const_str_true = 'testconst'
        const_str_false = ''
        """
        )
        collections_module = next(module["collections_module"].infer())
        self.assertTrue(collections_module.bool_value())
        function = module["function"]
        self.assertTrue(function.bool_value())
        klass = module["Class"]
        self.assertTrue(klass.bool_value())
        dict_comp = next(module["dict_comp"].infer())
        self.assertEqual(dict_comp, util.Uninferable)
        set_comp = next(module["set_comp"].infer())
        self.assertEqual(set_comp, util.Uninferable)
        list_comp = next(module["list_comp"].infer())
        self.assertEqual(list_comp, util.Uninferable)
        lambda_func = next(module["lambda_func"].infer())
        self.assertTrue(lambda_func)
        unbound_method = next(module["unbound_method"].infer())
        self.assertTrue(unbound_method)
        bound_method = next(module["bound_method"].infer())
        self.assertTrue(bound_method)
        generator = next(module["generator"].infer())
        self.assertTrue(generator)
        bin_op = module["bin_op"].parent.value
        self.assertIs(bin_op.bool_value(), util.Uninferable)
        bool_op = module["bool_op"].parent.value
        self.assertEqual(bool_op.bool_value(), util.Uninferable)
        callfunc = module["callfunc"].parent.value
        self.assertEqual(callfunc.bool_value(), util.Uninferable)
        good_callfunc = next(module["good_callfunc"].infer())
        self.assertTrue(good_callfunc.bool_value())
        compare = module["compare"].parent.value
        self.assertEqual(compare.bool_value(), util.Uninferable)

    def test_bool_value_instances(self) -> None:
        instances = extract_node(
            """
        class FalseBoolInstance(object):
            def __bool__(self):
                return False
        class TrueBoolInstance(object):
            def __bool__(self):
                return True
        class FalseLenInstance(object):
            def __len__(self):
                return 0
        class TrueLenInstance(object):
            def __len__(self):
                return 14
        class AlwaysTrueInstance(object):
            pass
        class ErrorInstance(object):
            def __bool__(self):
                return lala
            def __len__(self):
                return lala
        class NonMethods(object):
            __bool__ = 1
            __len__ = 2
        FalseBoolInstance() #@
        TrueBoolInstance() #@
        FalseLenInstance() #@
        TrueLenInstance() #@
        AlwaysTrueInstance() #@
        ErrorInstance() #@
        """
        )
        expected = (False, True, False, True, True, util.Uninferable, util.Uninferable)
        for node, expected_value in zip(instances, expected):
            inferred = next(node.infer())
            self.assertEqual(inferred.bool_value(), expected_value)

    def test_bool_value_variable(self) -> None:
        instance = extract_node(
            """
        class VariableBoolInstance(object):
            def __init__(self, value):
                self.value = value
            def __bool__(self):
                return self.value

        not VariableBoolInstance(True)
        """
        )
        inferred = next(instance.infer())
        self.assertIs(inferred.bool_value(), util.Uninferable)

    def test_infer_coercion_rules_for_floats_complex(self) -> None:
        ast_nodes = extract_node(
            """
        1 + 1.0 #@
        1 * 1.0 #@
        2 - 1.0 #@
        2 / 2.0 #@
        1 + 1j #@
        2 * 1j #@
        2 - 1j #@
        3 / 1j #@
        """
        )
        expected_values = [2.0, 1.0, 1.0, 1.0, 1 + 1j, 2j, 2 - 1j, -3j]
        for node, expected in zip(ast_nodes, expected_values):
            inferred = next(node.infer())
            self.assertEqual(inferred.value, expected)

    def test_binop_list_with_elts(self) -> None:
        ast_node = extract_node(
            """
        x = [A] * 1
        [1] + x
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, nodes.List)
        self.assertEqual(len(inferred.elts), 2)
        self.assertIsInstance(inferred.elts[0], nodes.Const)
        self.assertIsInstance(inferred.elts[1], nodes.Unknown)

    def test_binop_same_types(self) -> None:
        ast_nodes = extract_node(
            """
        class A(object):
            def __add__(self, other):
                return 42
        1 + 1 #@
        1 - 1 #@
        "a" + "b" #@
        A() + A() #@
        """
        )
        expected_values = [2, 0, "ab", 42]
        for node, expected in zip(ast_nodes, expected_values):
            inferred = next(node.infer())
            self.assertIsInstance(inferred, nodes.Const)
            self.assertEqual(inferred.value, expected)

    def test_binop_different_types_reflected_only(self) -> None:
        node = extract_node(
            """
        class A(object):
            pass
        class B(object):
            def __radd__(self, other):
                return other
        A() + B() #@
        """
        )
        inferred = next(node.infer())
        self.assertIsInstance(inferred, Instance)
        self.assertEqual(inferred.name, "A")

    def test_binop_different_types_unknown_bases(self) -> None:
        node = extract_node(
            """
        from foo import bar

        class A(bar):
            pass
        class B(object):
            def __radd__(self, other):
                return other
        A() + B() #@
        """
        )
        inferred = next(node.infer())
        self.assertIs(inferred, util.Uninferable)

    def test_binop_different_types_normal_not_implemented_and_reflected(self) -> None:
        node = extract_node(
            """
        class A(object):
            def __add__(self, other):
                return NotImplemented
        class B(object):
            def __radd__(self, other):
                return other
        A() + B() #@
        """
        )
        inferred = next(node.infer())
        self.assertIsInstance(inferred, Instance)
        self.assertEqual(inferred.name, "A")

    def test_binop_different_types_no_method_implemented(self) -> None:
        node = extract_node(
            """
        class A(object):
            pass
        class B(object): pass
        A() + B() #@
        """
        )
        inferred = next(node.infer())
        self.assertEqual(inferred, util.Uninferable)

    def test_binop_different_types_reflected_and_normal_not_implemented(self) -> None:
        node = extract_node(
            """
        class A(object):
            def __add__(self, other): return NotImplemented
        class B(object):
            def __radd__(self, other): return NotImplemented
        A() + B() #@
        """
        )
        inferred = next(node.infer())
        self.assertEqual(inferred, util.Uninferable)

    def test_binop_subtype(self) -> None:
        node = extract_node(
            """
        class A(object): pass
        class B(A):
            def __add__(self, other): return other
        B() + A() #@
        """
        )
        inferred = next(node.infer())
        self.assertIsInstance(inferred, Instance)
        self.assertEqual(inferred.name, "A")

    def test_binop_subtype_implemented_in_parent(self) -> None:
        node = extract_node(
            """
        class A(object):
            def __add__(self, other): return other
        class B(A): pass
        B() + A() #@
        """
        )
        inferred = next(node.infer())
        self.assertIsInstance(inferred, Instance)
        self.assertEqual(inferred.name, "A")

    def test_binop_subtype_not_implemented(self) -> None:
        node = extract_node(
            """
        class A(object):
            pass
        class B(A):
            def __add__(self, other): return NotImplemented
        B() + A() #@
        """
        )
        inferred = next(node.infer())
        self.assertEqual(inferred, util.Uninferable)

    def test_binop_supertype(self) -> None:
        node = extract_node(
            """
        class A(object):
            pass
        class B(A):
            def __radd__(self, other):
                 return other
        A() + B() #@
        """
        )
        inferred = next(node.infer())
        self.assertIsInstance(inferred, Instance)
        self.assertEqual(inferred.name, "A")

    def test_binop_supertype_rop_not_implemented(self) -> None:
        node = extract_node(
            """
        class A(object):
            def __add__(self, other):
                return other
        class B(A):
            def __radd__(self, other):
                 return NotImplemented
        A() + B() #@
        """
        )
        inferred = next(node.infer())
        self.assertIsInstance(inferred, Instance)
        self.assertEqual(inferred.name, "B")

    def test_binop_supertype_both_not_implemented(self) -> None:
        node = extract_node(
            """
        class A(object):
            def __add__(self): return NotImplemented
        class B(A):
            def __radd__(self, other):
                 return NotImplemented
        A() + B() #@
        """
        )
        inferred = next(node.infer())
        self.assertEqual(inferred, util.Uninferable)

    def test_binop_inference_errors(self) -> None:
        ast_nodes = extract_node(
            """
        from unknown import Unknown
        class A(object):
           def __add__(self, other): return NotImplemented
        class B(object):
           def __add__(self, other): return Unknown
        A() + Unknown #@
        Unknown + A() #@
        B() + A() #@
        A() + B() #@
        """
        )
        for node in ast_nodes:
            self.assertEqual(next(node.infer()), util.Uninferable)

    def test_binop_ambiguity(self) -> None:
        ast_nodes = extract_node(
            """
        class A(object):
           def __add__(self, other):
               if isinstance(other, B):
                    return NotImplemented
               if type(other) is type(self):
                    return 42
               return NotImplemented
        class B(A): pass
        class C(object):
           def __radd__(self, other):
               if isinstance(other, B):
                   return 42
               return NotImplemented
        A() + B() #@
        B() + A() #@
        A() + C() #@
        C() + A() #@
        """
        )
        for node in ast_nodes:
            self.assertEqual(next(node.infer()), util.Uninferable)

    def test_binop_self_in_list(self) -> None:
        """If 'self' is referenced within a list it should not be bound by it.

        Reported in https://github.com/pylint-dev/pylint/issues/4826.
        """
        ast_nodes = extract_node(
            """
        class A:
            def __init__(self):
                for a in [self] + []:
                    print(a) #@

        class B:
            def __init__(self):
                for b in [] + [self]:
                    print(b) #@
        """
        )
        inferred_a = list(ast_nodes[0].args[0].infer())
        self.assertEqual(len(inferred_a), 1)
        self.assertIsInstance(inferred_a[0], Instance)
        self.assertEqual(inferred_a[0]._proxied.name, "A")

        inferred_b = list(ast_nodes[1].args[0].infer())
        self.assertEqual(len(inferred_b), 1)
        self.assertIsInstance(inferred_b[0], Instance)
        self.assertEqual(inferred_b[0]._proxied.name, "B")

    def test_metaclass__getitem__(self) -> None:
        ast_node = extract_node(
            """
        class Meta(type):
            def __getitem__(cls, arg):
                return 24
        class A(object, metaclass=Meta):
            pass

        A['Awesome'] #@
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, nodes.Const)
        self.assertEqual(inferred.value, 24)

    @unittest.skipUnless(HAS_SIX, "These tests require the six library")
    def test_with_metaclass__getitem__(self):
        ast_node = extract_node(
            """
        class Meta(type):
            def __getitem__(cls, arg):
                return 24
        import six
        class A(six.with_metaclass(Meta)):
            pass

        A['Awesome'] #@
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, nodes.Const)
        self.assertEqual(inferred.value, 24)

    def test_bin_op_classes(self) -> None:
        ast_node = extract_node(
            """
        class Meta(type):
            def __or__(self, other):
                return 24
        class A(object, metaclass=Meta):
            pass

        A | A
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, nodes.Const)
        self.assertEqual(inferred.value, 24)

    @unittest.skipUnless(HAS_SIX, "These tests require the six library")
    def test_bin_op_classes_with_metaclass(self):
        ast_node = extract_node(
            """
        class Meta(type):
            def __or__(self, other):
                return 24
        import six
        class A(six.with_metaclass(Meta)):
            pass

        A | A
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, nodes.Const)
        self.assertEqual(inferred.value, 24)

    def test_bin_op_supertype_more_complicated_example(self) -> None:
        ast_node = extract_node(
            """
        class A(object):
            def __init__(self):
                self.foo = 42
            def __add__(self, other):
                return other.bar + self.foo / 2

        class B(A):
            def __init__(self):
                self.bar = 24
        def __radd__(self, other):
            return NotImplemented

        A() + B() #@
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, nodes.Const)
        self.assertEqual(int(inferred.value), 45)

    def test_aug_op_same_type_not_implemented(self) -> None:
        ast_node = extract_node(
            """
        class A(object):
            def __iadd__(self, other): return NotImplemented
            def __add__(self, other): return NotImplemented
        A() + A() #@
        """
        )
        self.assertEqual(next(ast_node.infer()), util.Uninferable)

    def test_aug_op_same_type_aug_implemented(self) -> None:
        ast_node = extract_node(
            """
        class A(object):
            def __iadd__(self, other): return other
        f = A()
        f += A() #@
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, Instance)
        self.assertEqual(inferred.name, "A")

    def test_aug_op_same_type_aug_not_implemented_normal_implemented(self) -> None:
        ast_node = extract_node(
            """
        class A(object):
            def __iadd__(self, other): return NotImplemented
            def __add__(self, other): return 42
        f = A()
        f += A() #@
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, nodes.Const)
        self.assertEqual(inferred.value, 42)

    def test_aug_op_subtype_both_not_implemented(self) -> None:
        ast_node = extract_node(
            """
        class A(object):
            def __iadd__(self, other): return NotImplemented
            def __add__(self, other): return NotImplemented
        class B(A):
            pass
        b = B()
        b+=A() #@
        """
        )
        self.assertEqual(next(ast_node.infer()), util.Uninferable)

    def test_aug_op_subtype_aug_op_is_implemented(self) -> None:
        ast_node = extract_node(
            """
        class A(object):
            def __iadd__(self, other): return 42
        class B(A):
            pass
        b = B()
        b+=A() #@
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, nodes.Const)
        self.assertEqual(inferred.value, 42)

    def test_aug_op_subtype_normal_op_is_implemented(self) -> None:
        ast_node = extract_node(
            """
        class A(object):
            def __add__(self, other): return 42
        class B(A):
            pass
        b = B()
        b+=A() #@
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, nodes.Const)
        self.assertEqual(inferred.value, 42)

    def test_aug_different_types_no_method_implemented(self) -> None:
        ast_node = extract_node(
            """
        class A(object): pass
        class B(object): pass
        f = A()
        f += B() #@
        """
        )
        self.assertEqual(next(ast_node.infer()), util.Uninferable)

    def test_aug_different_types_augop_implemented(self) -> None:
        ast_node = extract_node(
            """
        class A(object):
            def __iadd__(self, other): return other
        class B(object): pass
        f = A()
        f += B() #@
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, Instance)
        self.assertEqual(inferred.name, "B")

    def test_aug_different_types_aug_not_implemented(self) -> None:
        ast_node = extract_node(
            """
        class A(object):
            def __iadd__(self, other): return NotImplemented
            def __add__(self, other): return other
        class B(object): pass
        f = A()
        f += B() #@
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, Instance)
        self.assertEqual(inferred.name, "B")

    def test_aug_different_types_aug_not_implemented_rop_fallback(self) -> None:
        ast_node = extract_node(
            """
        class A(object):
            def __iadd__(self, other): return NotImplemented
            def __add__(self, other): return NotImplemented
        class B(object):
            def __radd__(self, other): return other
        f = A()
        f += B() #@
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, Instance)
        self.assertEqual(inferred.name, "A")

    def test_augop_supertypes_none_implemented(self) -> None:
        ast_node = extract_node(
            """
        class A(object): pass
        class B(object): pass
        a = A()
        a += B() #@
        """
        )
        self.assertEqual(next(ast_node.infer()), util.Uninferable)

    def test_augop_supertypes_not_implemented_returned_for_all(self) -> None:
        ast_node = extract_node(
            """
        class A(object):
            def __iadd__(self, other): return NotImplemented
            def __add__(self, other): return NotImplemented
        class B(object):
            def __add__(self, other): return NotImplemented
        a = A()
        a += B() #@
        """
        )
        self.assertEqual(next(ast_node.infer()), util.Uninferable)

    def test_augop_supertypes_augop_implemented(self) -> None:
        ast_node = extract_node(
            """
        class A(object):
            def __iadd__(self, other): return other
        class B(A): pass
        a = A()
        a += B() #@
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, Instance)
        self.assertEqual(inferred.name, "B")

    def test_augop_supertypes_reflected_binop_implemented(self) -> None:
        ast_node = extract_node(
            """
        class A(object):
            def __iadd__(self, other): return NotImplemented
        class B(A):
            def __radd__(self, other): return other
        a = A()
        a += B() #@
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, Instance)
        self.assertEqual(inferred.name, "A")

    def test_augop_supertypes_normal_binop_implemented(self) -> None:
        ast_node = extract_node(
            """
        class A(object):
            def __iadd__(self, other): return NotImplemented
            def __add__(self, other): return other
        class B(A):
            def __radd__(self, other): return NotImplemented

        a = A()
        a += B() #@
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, Instance)
        self.assertEqual(inferred.name, "B")

    def test_augop_type_errors_partially_uninferable(self) -> None:
        def patched_infer_augassign(context) -> None:
            return iter([util.BadBinaryOperationMessage(None, None, None), Uninferable])

        aug_op_node = extract_node("__name__ += 'test'")
        aug_op_node._infer_augassign = patched_infer_augassign
        errors = aug_op_node.type_errors()
        self.assertEqual(errors, [])

    def test_string_interpolation(self):
        ast_nodes = extract_node(
            """
        "a%d%d" % (1, 2) #@
        "a%(x)s" % {"x": 42} #@
        """
        )
        expected = ["a12", "a42"]
        for node, expected_value in zip(ast_nodes, expected):
            inferred = next(node.infer())
            self.assertIsInstance(inferred, nodes.Const)
            self.assertEqual(inferred.value, expected_value)

    def test_mul_list_supports__index__(self) -> None:
        ast_nodes = extract_node(
            """
        class Index(object):
            def __index__(self): return 2
        class NotIndex(object): pass
        class NotIndex2(object):
            def __index__(self): return None
        a = [1, 2]
        a * Index() #@
        a * NotIndex() #@
        a * NotIndex2() #@
        """
        )
        assert isinstance(ast_nodes, list)
        first = next(ast_nodes[0].infer())
        self.assertIsInstance(first, nodes.List)
        self.assertEqual([node.value for node in first.itered()], [1, 2, 1, 2])
        for rest in ast_nodes[1:]:
            inferred = next(rest.infer())
            self.assertEqual(inferred, util.Uninferable)

    def test_subscript_supports__index__(self) -> None:
        ast_nodes = extract_node(
            """
        class Index(object):
            def __index__(self): return 2
        class LambdaIndex(object):
            __index__ = lambda self: self.foo
            @property
            def foo(self): return 1
        class NonIndex(object):
            __index__ = lambda self: None
        a = [1, 2, 3, 4]
        a[Index()] #@
        a[LambdaIndex()] #@
        a[NonIndex()] #@
        """
        )
        assert isinstance(ast_nodes, list)
        first = next(ast_nodes[0].infer())
        self.assertIsInstance(first, nodes.Const)
        self.assertEqual(first.value, 3)
        second = next(ast_nodes[1].infer())
        self.assertIsInstance(second, nodes.Const)
        self.assertEqual(second.value, 2)
        self.assertRaises(InferenceError, next, ast_nodes[2].infer())

    def test_special_method_masquerading_as_another(self) -> None:
        ast_node = extract_node(
            """
        class Info(object):
            def __add__(self, other):
                return "lala"
            __or__ = __add__

        f = Info()
        f | Info() #@
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, nodes.Const)
        self.assertEqual(inferred.value, "lala")

    def test_unary_op_assignment(self) -> None:
        ast_node = extract_node(
            """
        class A(object): pass
        def pos(self):
            return 42
        A.__pos__ = pos
        f = A()
        +f #@
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, nodes.Const)
        self.assertEqual(inferred.value, 42)

    def test_unary_op_classes(self) -> None:
        ast_node = extract_node(
            """
        class Meta(type):
            def __invert__(self):
                return 42
        class A(object, metaclass=Meta):
            pass
        ~A
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, nodes.Const)
        self.assertEqual(inferred.value, 42)

    @unittest.skipUnless(HAS_SIX, "These tests require the six library")
    def test_unary_op_classes_with_metaclass(self):
        ast_node = extract_node(
            """
        import six
        class Meta(type):
            def __invert__(self):
                return 42
        class A(six.with_metaclass(Meta)):
            pass
        ~A
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, nodes.Const)
        self.assertEqual(inferred.value, 42)

    def _slicing_test_helper(
        self,
        pairs: tuple[
            tuple[str, list[int] | str],
            tuple[str, list[int] | str],
            tuple[str, list[int] | str],
            tuple[str, list[int] | str],
            tuple[str, list[int] | str],
            tuple[str, list[int] | str],
            tuple[str, list[int] | str],
            tuple[str, list[int] | str],
            tuple[str, list[int] | str],
            tuple[str, list[int] | str],
        ],
        cls: ABCMeta | type,
        get_elts: Callable,
    ) -> None:
        for code, expected in pairs:
            ast_node = extract_node(code)
            inferred = next(ast_node.infer())
            self.assertIsInstance(inferred, cls)
            self.assertEqual(get_elts(inferred), expected, ast_node.as_string())

    def test_slicing_list(self) -> None:
        pairs = (
            ("[1, 2, 3][:] #@", [1, 2, 3]),
            ("[1, 2, 3][0:] #@", [1, 2, 3]),
            ("[1, 2, 3][None:] #@", [1, 2, 3]),
            ("[1, 2, 3][None:None] #@", [1, 2, 3]),
            ("[1, 2, 3][0:-1] #@", [1, 2]),
            ("[1, 2, 3][0:2] #@", [1, 2]),
            ("[1, 2, 3][0:2:None] #@", [1, 2]),
            ("[1, 2, 3][::] #@", [1, 2, 3]),
            ("[1, 2, 3][::2] #@", [1, 3]),
            ("[1, 2, 3][::-1] #@", [3, 2, 1]),
            ("[1, 2, 3][0:2:2] #@", [1]),
            ("[1, 2, 3, 4, 5, 6][0:4-1:2+0] #@", [1, 3]),
        )
        self._slicing_test_helper(
            pairs, nodes.List, lambda inferred: [elt.value for elt in inferred.elts]
        )

    def test_slicing_tuple(self) -> None:
        pairs = (
            ("(1, 2, 3)[:] #@", [1, 2, 3]),
            ("(1, 2, 3)[0:] #@", [1, 2, 3]),
            ("(1, 2, 3)[None:] #@", [1, 2, 3]),
            ("(1, 2, 3)[None:None] #@", [1, 2, 3]),
            ("(1, 2, 3)[0:-1] #@", [1, 2]),
            ("(1, 2, 3)[0:2] #@", [1, 2]),
            ("(1, 2, 3)[0:2:None] #@", [1, 2]),
            ("(1, 2, 3)[::] #@", [1, 2, 3]),
            ("(1, 2, 3)[::2] #@", [1, 3]),
            ("(1, 2, 3)[::-1] #@", [3, 2, 1]),
            ("(1, 2, 3)[0:2:2] #@", [1]),
            ("(1, 2, 3, 4, 5, 6)[0:4-1:2+0] #@", [1, 3]),
        )
        self._slicing_test_helper(
            pairs, nodes.Tuple, lambda inferred: [elt.value for elt in inferred.elts]
        )

    def test_slicing_str(self) -> None:
        pairs = (
            ("'123'[:] #@", "123"),
            ("'123'[0:] #@", "123"),
            ("'123'[None:] #@", "123"),
            ("'123'[None:None] #@", "123"),
            ("'123'[0:-1] #@", "12"),
            ("'123'[0:2] #@", "12"),
            ("'123'[0:2:None] #@", "12"),
            ("'123'[::] #@", "123"),
            ("'123'[::2] #@", "13"),
            ("'123'[::-1] #@", "321"),
            ("'123'[0:2:2] #@", "1"),
            ("'123456'[0:4-1:2+0] #@", "13"),
        )
        self._slicing_test_helper(pairs, nodes.Const, lambda inferred: inferred.value)

    def test_invalid_slicing_primaries(self) -> None:
        examples = [
            "(lambda x: x)[1:2]",
            "1[2]",
            "(1, 2, 3)[a:]",
            "(1, 2, 3)[object:object]",
            "(1, 2, 3)[1:object]",
        ]
        for code in examples:
            node = extract_node(code)
            self.assertRaises(InferenceError, next, node.infer())

    def test_instance_slicing(self) -> None:
        ast_nodes = extract_node(
            """
        class A(object):
            def __getitem__(self, index):
                return [1, 2, 3, 4, 5][index]
        A()[1:] #@
        A()[:2] #@
        A()[1:4] #@
        """
        )
        expected_values = [[2, 3, 4, 5], [1, 2], [2, 3, 4]]
        for expected, node in zip(expected_values, ast_nodes):
            inferred = next(node.infer())
            self.assertIsInstance(inferred, nodes.List)
            self.assertEqual([elt.value for elt in inferred.elts], expected)

    def test_instance_slicing_slices(self) -> None:
        ast_node = extract_node(
            """
        class A(object):
            def __getitem__(self, index):
                return index
        A()[1:] #@
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, nodes.Slice)
        self.assertEqual(inferred.lower.value, 1)
        self.assertIsNone(inferred.upper)

    def test_instance_slicing_fails(self) -> None:
        ast_nodes = extract_node(
            """
        class A(object):
            def __getitem__(self, index):
                return 1[index]
        A()[4:5] #@
        A()[2:] #@
        """
        )
        for node in ast_nodes:
            self.assertEqual(next(node.infer()), util.Uninferable)

    def test_type__new__with_metaclass(self) -> None:
        ast_node = extract_node(
            """
        class Metaclass(type):
            pass
        class Entity(object):
             pass
        type.__new__(Metaclass, 'NewClass', (Entity,), {'a': 1}) #@
        """
        )
        inferred = next(ast_node.infer())

        self.assertIsInstance(inferred, nodes.ClassDef)
        self.assertEqual(inferred.name, "NewClass")
        metaclass = inferred.metaclass()
        self.assertEqual(metaclass, inferred.root()["Metaclass"])
        ancestors = list(inferred.ancestors())
        self.assertEqual(len(ancestors), 2)
        self.assertEqual(ancestors[0], inferred.root()["Entity"])
        attributes = inferred.getattr("a")
        self.assertEqual(len(attributes), 1)
        self.assertIsInstance(attributes[0], nodes.Const)
        self.assertEqual(attributes[0].value, 1)

    def test_type__new__not_enough_arguments(self) -> None:
        ast_nodes = extract_node(
            """
        type.__new__(type, 'foo') #@
        type.__new__(type, 'foo', ()) #@
        type.__new__(type, 'foo', (), {}, ()) #@
        """
        )
        for node in ast_nodes:
            with pytest.raises(InferenceError):
                next(node.infer())

    def test_type__new__invalid_mcs_argument(self) -> None:
        ast_nodes = extract_node(
            """
        class Class(object): pass
        type.__new__(1, 2, 3, 4) #@
        type.__new__(Class, 2, 3, 4) #@
        """
        )
        for node in ast_nodes:
            with pytest.raises(InferenceError):
                next(node.infer())

    def test_type__new__invalid_name(self) -> None:
        ast_nodes = extract_node(
            """
        class Class(type): pass
        type.__new__(Class, object, 1, 2) #@
        type.__new__(Class, 1, 1, 2) #@
        type.__new__(Class, [], 1, 2) #@
        """
        )
        for node in ast_nodes:
            with pytest.raises(InferenceError):
                next(node.infer())

    def test_type__new__invalid_bases(self) -> None:
        ast_nodes = extract_node(
            """
        type.__new__(type, 'a', 1, 2) #@
        type.__new__(type, 'a', [], 2) #@
        type.__new__(type, 'a', {}, 2) #@
        type.__new__(type, 'a', (1, ), 2) #@
        type.__new__(type, 'a', (object, 1), 2) #@
        """
        )
        for node in ast_nodes:
            with pytest.raises(InferenceError):
                next(node.infer())

    def test_type__new__invalid_attrs(self) -> None:
        type_error_nodes = extract_node(
            """
        type.__new__(type, 'a', (), ()) #@
        type.__new__(type, 'a', (), object) #@
        type.__new__(type, 'a', (), 1) #@
        """
        )
        for node in type_error_nodes:
            with pytest.raises(InferenceError):
                next(node.infer())

        # Ignore invalid keys
        ast_nodes = extract_node(
            """
            type.__new__(type, 'a', (), {object: 1}) #@
            type.__new__(type, 'a', (), {1:2, "a":5}) #@
        """
        )
        for node in ast_nodes:
            inferred = next(node.infer())
            self.assertIsInstance(inferred, nodes.ClassDef)

    def test_type__new__metaclass_lookup(self) -> None:
        ast_node = extract_node(
            """
        class Metaclass(type):
            def test(cls): pass
            @classmethod
            def test1(cls): pass
            attr = 42
        type.__new__(Metaclass, 'A', (), {}) #@
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, nodes.ClassDef)
        test = inferred.getattr("test")
        self.assertEqual(len(test), 1)
        self.assertIsInstance(test[0], BoundMethod)
        self.assertIsInstance(test[0].bound, nodes.ClassDef)
        self.assertEqual(test[0].bound, inferred)
        test1 = inferred.getattr("test1")
        self.assertEqual(len(test1), 1)
        self.assertIsInstance(test1[0], BoundMethod)
        self.assertIsInstance(test1[0].bound, nodes.ClassDef)
        self.assertEqual(test1[0].bound, inferred.metaclass())
        attr = inferred.getattr("attr")
        self.assertEqual(len(attr), 1)
        self.assertIsInstance(attr[0], nodes.Const)
        self.assertEqual(attr[0].value, 42)

    def test_type__new__metaclass_and_ancestors_lookup(self) -> None:
        ast_node = extract_node(
            """
        class Book(object):
             title = 'Ubik'
        class MetaBook(type):
             title = 'Grimus'
        type.__new__(MetaBook, 'book', (Book, ), {'title':'Catch 22'}) #@
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, nodes.ClassDef)
        titles = [
            title.value
            for attr in inferred.getattr("title")
            for title in attr.inferred()
        ]
        self.assertEqual(titles, ["Catch 22", "Ubik", "Grimus"])

    @staticmethod
    def test_builtin_new() -> None:
        ast_node = extract_node("int.__new__(int, 42)")
        inferred = next(ast_node.infer())
        assert isinstance(inferred, nodes.Const)
        assert inferred.value == 42

        ast_node2 = extract_node("int.__new__(int)")
        inferred2 = next(ast_node2.infer())
        assert isinstance(inferred2, Instance)
        assert not isinstance(inferred2, nodes.Const)
        assert inferred2._proxied is inferred._proxied

        ast_node3 = extract_node(
            """
        x = 43
        int.__new__(int, x)  #@
        """
        )
        inferred3 = next(ast_node3.infer())
        assert isinstance(inferred3, nodes.Const)
        assert inferred3.value == 43

        ast_node4 = extract_node("int.__new__()")
        with pytest.raises(InferenceError):
            next(ast_node4.infer())

        ast_node5 = extract_node(
            """
        class A:  pass
        A.__new__(A())  #@
        """
        )
        with pytest.raises(InferenceError):
            next(ast_node5.infer())

        ast_nodes6 = extract_node(
            """
        class A:  pass
        class B(A):  pass
        class C: pass
        A.__new__(A)  #@
        A.__new__(B)  #@
        B.__new__(A)  #@
        B.__new__(B)  #@
        C.__new__(A)  #@
        """
        )
        instance_A1 = next(ast_nodes6[0].infer())
        assert instance_A1._proxied.name == "A"
        instance_B1 = next(ast_nodes6[1].infer())
        assert instance_B1._proxied.name == "B"
        instance_A2 = next(ast_nodes6[2].infer())
        assert instance_A2._proxied.name == "A"
        instance_B2 = next(ast_nodes6[3].infer())
        assert instance_B2._proxied.name == "B"
        instance_A3 = next(ast_nodes6[4].infer())
        assert instance_A3._proxied.name == "A"

        ast_nodes7 = extract_node(
            """
        import enum
        class A(enum.EnumMeta): pass
        class B(enum.EnumMeta):
            def __new__(mcs, value, **kwargs):
                return super().__new__(mcs, "str", (enum.Enum,), enum._EnumDict(), **kwargs)
        class C(enum.EnumMeta):
            def __new__(mcs, **kwargs):
                return super().__new__(A, "str", (enum.Enum,), enum._EnumDict(), **kwargs)
        B("")  #@
        C()  #@
        """
        )
        instance_B = next(ast_nodes7[0].infer())
        assert instance_B._proxied.name == "B"
        instance_C = next(ast_nodes7[1].infer())
        # TODO: This should be A. However, we don't infer EnumMeta.__new__
        # correctly.
        assert instance_C._proxied.name == "C"

    @pytest.mark.xfail(reason="Does not support function metaclasses")
    def test_function_metaclasses(self):
        # These are not supported right now, although
        # they will be in the future.
        ast_node = extract_node(
            """
        class BookMeta(type):
            author = 'Rushdie'

        def metaclass_function(*args):
            return BookMeta

        class Book(object, metaclass=metaclass_function):
            pass
        Book #@
        """
        )
        inferred = next(ast_node.infer())
        metaclass = inferred.metaclass()
        self.assertIsInstance(metaclass, nodes.ClassDef)
        self.assertEqual(metaclass.name, "BookMeta")
        author = next(inferred.igetattr("author"))
        self.assertIsInstance(author, nodes.Const)
        self.assertEqual(author.value, "Rushdie")

    def test_subscript_inference_error(self) -> None:
        # Used to raise StopIteration
        ast_node = extract_node(
            """
        class AttributeDict(dict):
            def __getitem__(self, name):
                return self
        flow = AttributeDict()
        flow['app'] = AttributeDict()
        flow['app']['config'] = AttributeDict()
        flow['app']['config']['doffing'] = AttributeDict() #@
        """
        )
        self.assertIsInstance(util.safe_infer(ast_node.targets[0]), Instance)

    def test_classmethod_inferred_by_context(self) -> None:
        ast_node = extract_node(
            """
        class Super(object):
           def instance(cls):
              return cls()
           instance = classmethod(instance)

        class Sub(Super):
            def method(self):
                return self

        # should see the Sub.instance() is returning a Sub
        # instance, not a Super instance
        Sub.instance().method() #@
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, Instance)
        self.assertEqual(inferred.name, "Sub")

    def test_infer_call_result_invalid_dunder_call_on_instance(self) -> None:
        ast_nodes = extract_node(
            """
        class A:
            __call__ = 42
        class B:
            __call__ = A()
        class C:
            __call = None
        A() #@
        B() #@
        C() #@
        """
        )
        for node in ast_nodes:
            inferred = next(node.infer())
            self.assertRaises(InferenceError, next, inferred.infer_call_result(node))

    def test_infer_call_result_same_proxied_class(self) -> None:
        node = extract_node(
            """
        class A:
            __call__ = A()
        A() #@
        """
        )
        inferred = next(node.infer())
        fully_evaluated_inference_results = list(inferred.infer_call_result(node))
        assert fully_evaluated_inference_results[0].name == "A"

    def test_infer_call_result_with_metaclass(self) -> None:
        node = extract_node("def with_metaclass(meta, *bases): return 42")
        inferred = next(node.infer_call_result(caller=node))
        self.assertIsInstance(inferred, nodes.Const)

    def test_context_call_for_context_managers(self) -> None:
        ast_nodes = extract_node(
            """
        class A:
            def __enter__(self):
                return self
        class B:
            __enter__ = lambda self: self
        class C:
            @property
            def a(self): return A()
            def __enter__(self):
                return self.a
        with A() as a:
            a #@
        with B() as b:
            b #@
        with C() as c:
            c #@
        """
        )
        assert isinstance(ast_nodes, list)
        first_a = next(ast_nodes[0].infer())
        self.assertIsInstance(first_a, Instance)
        self.assertEqual(first_a.name, "A")
        second_b = next(ast_nodes[1].infer())
        self.assertIsInstance(second_b, Instance)
        self.assertEqual(second_b.name, "B")
        third_c = next(ast_nodes[2].infer())
        self.assertIsInstance(third_c, Instance)
        self.assertEqual(third_c.name, "A")

    def test_metaclass_subclasses_arguments_are_classes_not_instances(self) -> None:
        ast_node = extract_node(
            """
        class A(type):
            def test(cls):
                return cls
        class B(object, metaclass=A):
            pass

        B.test() #@
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, nodes.ClassDef)
        self.assertEqual(inferred.name, "B")

    @unittest.skipUnless(HAS_SIX, "These tests require the six library")
    def test_with_metaclass_subclasses_arguments_are_classes_not_instances(self):
        ast_node = extract_node(
            """
        class A(type):
            def test(cls):
                return cls
        import six
        class B(six.with_metaclass(A)):
            pass

        B.test() #@
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, nodes.ClassDef)
        self.assertEqual(inferred.name, "B")

    @unittest.skipUnless(HAS_SIX, "These tests require the six library")
    def test_with_metaclass_with_partial_imported_name(self):
        ast_node = extract_node(
            """
        class A(type):
            def test(cls):
                return cls
        from six import with_metaclass
        class B(with_metaclass(A)):
            pass

        B.test() #@
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, nodes.ClassDef)
        self.assertEqual(inferred.name, "B")

    def test_infer_cls_in_class_methods(self) -> None:
        ast_nodes = extract_node(
            """
        class A(type):
            def __call__(cls):
                cls #@
        class B(object):
            def __call__(cls):
                cls #@
        """
        )
        assert isinstance(ast_nodes, list)
        first = next(ast_nodes[0].infer())
        self.assertIsInstance(first, nodes.ClassDef)
        second = next(ast_nodes[1].infer())
        self.assertIsInstance(second, Instance)

    @pytest.mark.xfail(reason="Metaclass arguments not inferred as classes")
    def test_metaclass_arguments_are_classes_not_instances(self):
        ast_node = extract_node(
            """
        class A(type):
            def test(cls): return cls
        A.test() #@
        """
        )
        # This is not supported yet
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, nodes.ClassDef)
        self.assertEqual(inferred.name, "A")

    def test_metaclass_with_keyword_args(self) -> None:
        ast_node = extract_node(
            """
        class TestMetaKlass(type):
            def __new__(mcs, name, bases, ns, kwo_arg):
                return super().__new__(mcs, name, bases, ns)

        class TestKlass(metaclass=TestMetaKlass, kwo_arg=42): #@
            pass
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, nodes.ClassDef)

    def test_metaclass_custom_dunder_call(self) -> None:
        """The Metaclass __call__ should take precedence
        over the default metaclass type call (initialization).

        See https://github.com/pylint-dev/pylint/issues/2159
        """
        val = (
            extract_node(
                """
        class _Meta(type):
            def __call__(cls):
                return 1
        class Clazz(metaclass=_Meta):
            def __call__(self):
                return 5.5

        Clazz() #@
        """
            )
            .inferred()[0]
            .value
        )
        assert val == 1

    def test_metaclass_custom_dunder_call_boundnode(self) -> None:
        """The boundnode should be the calling class."""
        cls = extract_node(
            """
        class _Meta(type):
            def __call__(cls):
                return cls
        class Clazz(metaclass=_Meta):
            pass
        Clazz() #@
        """
        ).inferred()[0]
        assert isinstance(cls, Instance) and cls.name == "Clazz"

    def test_infer_subclass_attr_outer_class(self) -> None:
        node = extract_node(
            """
        class Outer:
            data = 123

        class Test(Outer):
            pass
        Test.data
        """
        )
        inferred = next(node.infer())
        assert isinstance(inferred, nodes.Const)
        assert inferred.value == 123

    def test_infer_subclass_attr_inner_class_works_indirectly(self) -> None:
        node = extract_node(
            """
        class Outer:
            class Inner:
                data = 123
        Inner = Outer.Inner

        class Test(Inner):
            pass
        Test.data
        """
        )
        inferred = next(node.infer())
        assert isinstance(inferred, nodes.Const)
        assert inferred.value == 123

    def test_infer_subclass_attr_inner_class(self) -> None:
        clsdef_node, attr_node = extract_node(
            """
        class Outer:
            class Inner:
                data = 123

        class Test(Outer.Inner):
            pass
        Test  #@
        Test.data  #@
            """
        )
        clsdef = next(clsdef_node.infer())
        assert isinstance(clsdef, nodes.ClassDef)
        inferred = next(clsdef.igetattr("data"))
        assert isinstance(inferred, nodes.Const)
        assert inferred.value == 123
        # Inferring the value of .data via igetattr() worked before the
        # old_boundnode fixes in infer_subscript, so it should have been
        # possible to infer the subscript directly. It is the difference
        # between these two cases that led to the discovery of the cause of the
        # bug in https://github.com/pylint-dev/astroid/issues/904
        inferred = next(attr_node.infer())
        assert isinstance(inferred, nodes.Const)
        assert inferred.value == 123

    def test_infer_method_empty_body(self) -> None:
        # https://github.com/PyCQA/astroid/issues/1015
        node = extract_node(
            """
            class A:
                def foo(self): ...

            A().foo()  #@
        """
        )
        inferred = next(node.infer())
        assert isinstance(inferred, nodes.Const)
        assert inferred.value is None

    def test_infer_method_overload(self) -> None:
        # https://github.com/PyCQA/astroid/issues/1015
        node = extract_node(
            """
            class A:
                def foo(self): ...

                def foo(self):
                    yield

            A().foo()  #@
        """
        )
        inferred = list(node.infer())
        assert len(inferred) == 1
        assert isinstance(inferred[0], Generator)

    def test_infer_function_under_if(self) -> None:
        node = extract_node(
            """
        if 1 in [1]:
            def func():
                return 42
        else:
            def func():
                return False

        func()  #@
        """
        )
        inferred = list(node.inferred())
        assert [const.value for const in inferred] == [42, False]

    def test_infer_property_setter(self) -> None:
        node = extract_node(
            """
        class PropertyWithSetter:
            @property
            def host(self):
                return self._host

            @host.setter
            def host(self, value: str):
                self._host = value

        PropertyWithSetter().host #@
        """
        )
        assert not isinstance(next(node.infer()), Instance)

    def test_delayed_attributes_without_slots(self) -> None:
        ast_node = extract_node(
            """
        class A(object):
            __slots__ = ('a', )
        a = A()
        a.teta = 24
        a.a = 24
        a #@
        """
        )
        inferred = next(ast_node.infer())
        with self.assertRaises(NotFoundError):
            inferred.getattr("teta")
        inferred.getattr("a")

    def test_lambda_as_methods(self) -> None:
        ast_node = extract_node(
            """
        class X:
           m = lambda self, arg: self.z + arg
           z = 24

        X().m(4) #@
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, nodes.Const)
        self.assertEqual(inferred.value, 28)

    def test_inner_value_redefined_by_subclass(self) -> None:
        ast_node = extract_node(
            """
        class X(object):
            M = lambda self, arg: "a"
            x = 24
            def __init__(self):
                x = 24
                self.m = self.M(x)

        class Y(X):
            M = lambda self, arg: arg + 1
            def blurb(self):
                self.m #@
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, nodes.Const)
        self.assertEqual(inferred.value, 25)

    def test_inner_value_redefined_by_subclass_with_mro(self) -> None:
        ast_node = extract_node(
            """
        class X(object):
            M = lambda self, arg: arg + 1
            x = 24
            def __init__(self):
                y = self
                self.m = y.M(1) + y.z

        class C(object):
            z = 24

        class Y(X, C):
            M = lambda self, arg: arg + 1
            def blurb(self):
                self.m #@
        """
        )
        inferred = next(ast_node.infer())
        assert isinstance(inferred, nodes.Const)
        assert inferred.value == 26

    def test_getitem_of_class_raised_type_error(self) -> None:
        # Test that we wrap an AttributeInferenceError
        # and reraise it as a TypeError in Class.getitem
        node = extract_node(
            """
        def test(): ...
        test()
        """
        )
        inferred = next(node.infer())
        with self.assertRaises(AstroidTypeError):
            inferred.getitem(nodes.Const("4"))

    def test_infer_arg_called_type_is_uninferable(self) -> None:
        node = extract_node(
            """
        def func(type):
            type #@
        """
        )
        inferred = next(node.infer())
        assert inferred is util.Uninferable

    def test_infer_arg_called_object_when_used_as_index_is_uninferable(self) -> None:
        node = extract_node(
            """
        def func(object):
            ['list'][
                object #@
            ]
        """
        )
        inferred = next(node.infer())
        assert inferred is util.Uninferable

    def test_infer_arg_called_type_when_used_as_index_is_uninferable(self):
        # https://github.com/pylint-dev/astroid/pull/958
        node = extract_node(
            """
        def func(type):
            ['list'][
                type #@
            ]
        """
        )
        inferred = next(node.infer())
        assert not isinstance(inferred, nodes.ClassDef)  # was inferred as builtins.type
        assert inferred is util.Uninferable

    def test_infer_arg_called_type_when_used_as_subscript_is_uninferable(self):
        # https://github.com/pylint-dev/astroid/pull/958
        node = extract_node(
            """
        def func(type):
            type[0] #@
        """
        )
        inferred = next(node.infer())
        assert not isinstance(inferred, nodes.ClassDef)  # was inferred as builtins.type
        assert inferred is util.Uninferable

    def test_infer_arg_called_type_defined_in_outer_scope_is_uninferable(self):
        # https://github.com/pylint-dev/astroid/pull/958
        node = extract_node(
            """
        def outer(type):
            def inner():
                type[0] #@
        """
        )
        inferred = next(node.infer())
        assert not isinstance(inferred, nodes.ClassDef)  # was inferred as builtins.type
        assert inferred is util.Uninferable

    def test_infer_subclass_attr_instance_attr_indirect(self) -> None:
        node = extract_node(
            """
        class Parent:
            def __init__(self):
                self.data = 123

        class Test(Parent):
            pass
        t = Test()
        t
        """
        )
        inferred = next(node.infer())
        assert isinstance(inferred, Instance)
        const = next(inferred.igetattr("data"))
        assert isinstance(const, nodes.Const)
        assert const.value == 123

    def test_infer_subclass_attr_instance_attr(self) -> None:
        node = extract_node(
            """
        class Parent:
            def __init__(self):
                self.data = 123

        class Test(Parent):
            pass
        t = Test()
        t.data
        """
        )
        inferred = next(node.infer())
        assert isinstance(inferred, nodes.Const)
        assert inferred.value == 123

    def test_uninferable_type_subscript(self) -> None:
        node = extract_node("[type for type in [] if type['id']]")
        with self.assertRaises(InferenceError):
            _ = next(node.infer())


class GetattrTest(unittest.TestCase):
    def test_yes_when_unknown(self) -> None:
        ast_nodes = extract_node(
            """
        from missing import Missing
        getattr(1, Unknown) #@
        getattr(Unknown, 'a') #@
        getattr(Unknown, Unknown) #@
        getattr(Unknown, Unknown, Unknown) #@

        getattr(Missing, 'a') #@
        getattr(Missing, Missing) #@
        getattr('a', Missing) #@
        getattr('a', Missing, Missing) #@
        """
        )
        for node in ast_nodes[:4]:
            self.assertRaises(InferenceError, next, node.infer())

        for node in ast_nodes[4:]:
            inferred = next(node.infer())
            self.assertEqual(inferred, util.Uninferable, node)

    def test_attrname_not_string(self) -> None:
        ast_nodes = extract_node(
            """
        getattr(1, 1) #@
        c = int
        getattr(1, c) #@
        """
        )
        for node in ast_nodes:
            self.assertRaises(InferenceError, next, node.infer())

    def test_attribute_missing(self) -> None:
        ast_nodes = extract_node(
            """
        getattr(1, 'ala') #@
        getattr(int, 'ala') #@
        getattr(float, 'bala') #@
        getattr({}, 'portocala') #@
        """
        )
        for node in ast_nodes:
            self.assertRaises(InferenceError, next, node.infer())

    def test_default(self) -> None:
        ast_nodes = extract_node(
            """
        getattr(1, 'ala', None) #@
        getattr(int, 'bala', int) #@
        getattr(int, 'bala', getattr(int, 'portocala', None)) #@
        """
        )
        assert isinstance(ast_nodes, list)
        first = next(ast_nodes[0].infer())
        self.assertIsInstance(first, nodes.Const)
        self.assertIsNone(first.value)

        second = next(ast_nodes[1].infer())
        self.assertIsInstance(second, nodes.ClassDef)
        self.assertEqual(second.qname(), "builtins.int")

        third = next(ast_nodes[2].infer())
        self.assertIsInstance(third, nodes.Const)
        self.assertIsNone(third.value)

    def test_lookup(self) -> None:
        ast_nodes = extract_node(
            """
        class A(object):
            def test(self): pass
        class B(A):
            def test_b(self): pass
        class C(A): pass
        class E(C, B):
            def test_e(self): pass

        getattr(A(), 'test') #@
        getattr(A, 'test') #@
        getattr(E(), 'test_b') #@
        getattr(E(), 'test') #@

        class X(object):
            def test(self):
                getattr(self, 'test') #@
        """
        )
        assert isinstance(ast_nodes, list)
        first = next(ast_nodes[0].infer())
        self.assertIsInstance(first, BoundMethod)
        self.assertEqual(first.bound.name, "A")

        second = next(ast_nodes[1].infer())
        self.assertIsInstance(second, UnboundMethod)
        self.assertIsInstance(second.parent, nodes.ClassDef)
        self.assertEqual(second.parent.name, "A")

        third = next(ast_nodes[2].infer())
        self.assertIsInstance(third, BoundMethod)
        # Bound to E, but the provider is B.
        self.assertEqual(third.bound.name, "E")
        self.assertEqual(third._proxied._proxied.parent.name, "B")

        fourth = next(ast_nodes[3].infer())
        self.assertIsInstance(fourth, BoundMethod)
        self.assertEqual(fourth.bound.name, "E")
        self.assertEqual(third._proxied._proxied.parent.name, "B")

        fifth = next(ast_nodes[4].infer())
        self.assertIsInstance(fifth, BoundMethod)
        self.assertEqual(fifth.bound.name, "X")

    def test_lambda(self) -> None:
        node = extract_node(
            """
        getattr(lambda x: x, 'f') #@
        """
        )
        inferred = next(node.infer())
        self.assertEqual(inferred, util.Uninferable)


class HasattrTest(unittest.TestCase):
    def test_inference_errors(self) -> None:
        ast_nodes = extract_node(
            """
        from missing import Missing

        hasattr(Unknown, 'ala') #@

        hasattr(Missing, 'bala') #@
        hasattr('portocala', Missing) #@
        """
        )
        for node in ast_nodes:
            inferred = next(node.infer())
            self.assertEqual(inferred, util.Uninferable)

    def test_attribute_is_missing(self) -> None:
        ast_nodes = extract_node(
            """
        class A: pass
        hasattr(int, 'ala') #@
        hasattr({}, 'bala') #@
        hasattr(A(), 'portocala') #@
        """
        )
        for node in ast_nodes:
            inferred = next(node.infer())
            self.assertIsInstance(inferred, nodes.Const)
            self.assertFalse(inferred.value)

    def test_attribute_is_not_missing(self) -> None:
        ast_nodes = extract_node(
            """
        class A(object):
            def test(self): pass
        class B(A):
            def test_b(self): pass
        class C(A): pass
        class E(C, B):
            def test_e(self): pass

        hasattr(A(), 'test') #@
        hasattr(A, 'test') #@
        hasattr(E(), 'test_b') #@
        hasattr(E(), 'test') #@

        class X(object):
            def test(self):
                hasattr(self, 'test') #@
        """
        )
        for node in ast_nodes:
            inferred = next(node.infer())
            self.assertIsInstance(inferred, nodes.Const)
            self.assertTrue(inferred.value)

    def test_lambda(self) -> None:
        node = extract_node(
            """
        hasattr(lambda x: x, 'f') #@
        """
        )
        inferred = next(node.infer())
        self.assertIsInstance(inferred, nodes.Const)
        self.assertIs(inferred.value, False)


class BoolOpTest(unittest.TestCase):
    def test_bool_ops(self) -> None:
        expected = [
            ("1 and 2", 2),
            ("0 and 2", 0),
            ("1 or 2", 1),
            ("0 or 2", 2),
            ("0 or 0 or 1", 1),
            ("1 and 2 and 3", 3),
            ("1 and 2 or 3", 2),
            ("1 and 0 or 3", 3),
            ("1 or 0 and 2", 1),
            ("(1 and 2) and (2 and 3)", 3),
            ("not 2 and 3", False),
            ("2 and not 3", False),
            ("not 0 and 3", 3),
            ("True and False", False),
            ("not (True or False) and True", False),
        ]
        for code, expected_value in expected:
            node = extract_node(code)
            inferred = next(node.infer())
            self.assertEqual(inferred.value, expected_value)

    def test_yes_when_unknown(self) -> None:
        ast_nodes = extract_node(
            """
        from unknown import unknown, any, not_any
        0 and unknown #@
        unknown or 0 #@
        any or not_any and unknown #@
        """
        )
        for node in ast_nodes:
            inferred = next(node.infer())
            self.assertEqual(inferred, util.Uninferable)

    def test_other_nodes(self) -> None:
        ast_nodes = extract_node(
            """
        def test(): pass
        test and 0 #@
        1 and test #@
        """
        )
        assert isinstance(ast_nodes, list)
        first = next(ast_nodes[0].infer())
        self.assertEqual(first.value, 0)
        second = next(ast_nodes[1].infer())
        self.assertIsInstance(second, nodes.FunctionDef)
        self.assertEqual(second.name, "test")


class TestCallable(unittest.TestCase):
    def test_callable(self) -> None:
        expected = [
            ("callable(len)", True),
            ('callable("a")', False),
            ("callable(callable)", True),
            ("callable(lambda x, y: x+y)", True),
            ("import os; __(callable(os))", False),
            ("callable(int)", True),
            (
                """
             def test(): pass
             callable(test) #@""",
                True,
            ),
            (
                """
             class C1:
                def meth(self): pass
             callable(C1) #@""",
                True,
            ),
        ]
        for code, expected_value in expected:
            node = extract_node(code)
            inferred = next(node.infer())
            self.assertEqual(inferred.value, expected_value)

    def test_callable_methods(self) -> None:
        ast_nodes = extract_node(
            """
        class C:
            def test(self): pass
            @staticmethod
            def static(): pass
            @classmethod
            def class_method(cls): pass
            def __call__(self): pass
        class D(C):
            pass
        class NotReallyCallableDueToPythonMisfeature(object):
            __call__ = 42
        callable(C.test) #@
        callable(C.static) #@
        callable(C.class_method) #@
        callable(C().test) #@
        callable(C().static) #@
        callable(C().class_method) #@
        C #@
        C() #@
        NotReallyCallableDueToPythonMisfeature() #@
        staticmethod #@
        classmethod #@
        property #@
        D #@
        D() #@
        """
        )
        for node in ast_nodes:
            inferred = next(node.infer())
            self.assertTrue(inferred)

    def test_inference_errors(self) -> None:
        ast_nodes = extract_node(
            """
        from unknown import unknown
        callable(unknown) #@
        def test():
            return unknown
        callable(test()) #@
        """
        )
        for node in ast_nodes:
            inferred = next(node.infer())
            self.assertEqual(inferred, util.Uninferable)

    def test_not_callable(self) -> None:
        ast_nodes = extract_node(
            """
        callable("") #@
        callable(1) #@
        callable(True) #@
        """
        )
        for node in ast_nodes:
            inferred = next(node.infer())
            self.assertFalse(inferred.value)


class TestBool(unittest.TestCase):
    def test_bool(self) -> None:
        pairs = [
            ("bool()", False),
            ("bool(1)", True),
            ("bool(0)", False),
            ("bool([])", False),
            ("bool([1])", True),
            ("bool({})", False),
            ("bool(True)", True),
            ("bool(False)", False),
            ("bool(None)", False),
            ("from unknown import Unknown; __(bool(Unknown))", util.Uninferable),
        ]
        for code, expected in pairs:
            node = extract_node(code)
            inferred = next(node.infer())
            if expected is util.Uninferable:
                self.assertEqual(expected, inferred)
            else:
                self.assertEqual(inferred.value, expected)

    def test_bool_bool_special_method(self) -> None:
        ast_nodes = extract_node(
            """
        class FalseClass:
           def __bool__(self):
               return False
        class TrueClass:
           def __bool__(self):
               return True
        class C(object):
           def __call__(self):
               return False
        class B(object):
           __bool__ = C()
        class LambdaBoolFalse(object):
            __bool__ = lambda self: self.foo
            @property
            def foo(self): return 0
        class FalseBoolLen(object):
            __len__ = lambda self: self.foo
            @property
            def foo(self): return 0
        bool(FalseClass) #@
        bool(TrueClass) #@
        bool(FalseClass()) #@
        bool(TrueClass()) #@
        bool(B()) #@
        bool(LambdaBoolFalse()) #@
        bool(FalseBoolLen()) #@
        """
        )
        expected = [True, True, False, True, False, False, False]
        for node, expected_value in zip(ast_nodes, expected):
            inferred = next(node.infer())
            self.assertEqual(inferred.value, expected_value)

    def test_bool_instance_not_callable(self) -> None:
        ast_nodes = extract_node(
            """
        class BoolInvalid(object):
           __bool__ = 42
        class LenInvalid(object):
           __len__ = "a"
        bool(BoolInvalid()) #@
        bool(LenInvalid()) #@
        """
        )
        for node in ast_nodes:
            inferred = next(node.infer())
            self.assertEqual(inferred, util.Uninferable)

    def test_class_subscript(self) -> None:
        node = extract_node(
            """
        class Foo:
            def __class_getitem__(cls, *args, **kwargs):
                return cls

        Foo[int]
        """
        )
        inferred = next(node.infer())
        self.assertIsInstance(inferred, nodes.ClassDef)
        self.assertEqual(inferred.name, "Foo")

    def test_class_subscript_inference_context(self) -> None:
        """Context path has a reference to any parents inferred by getitem()."""
        code = """
        class Parent: pass

        class A(Parent):
            def __class_getitem__(self, value):
                return cls
        """
        klass = extract_node(code)
        context = InferenceContext()
        # For this test, we want a fresh inference, rather than a cache hit on
        # the inference done at brain time in _is_enum_subclass()
        context.lookupname = "Fresh lookup!"
        _ = klass.getitem(0, context=context)

        assert next(iter(context.path))[0].name == "Parent"


class TestType(unittest.TestCase):
    def test_type(self) -> None:
        pairs = [
            ("type(1)", "int"),
            ("type(type)", "type"),
            ("type(None)", "NoneType"),
            ("type(object)", "type"),
            ("type(dict())", "dict"),
            ("type({})", "dict"),
            ("type(frozenset())", "frozenset"),
        ]
        for code, expected in pairs:
            node = extract_node(code)
            inferred = next(node.infer())
            self.assertIsInstance(inferred, nodes.ClassDef)
            self.assertEqual(inferred.name, expected)


class ArgumentsTest(unittest.TestCase):
    @staticmethod
    def _get_dict_value(
        inferred: dict,
    ) -> list[tuple[str, int]] | list[tuple[str, str]]:
        items = inferred.items
        return sorted((key.value, value.value) for key, value in items)

    @staticmethod
    def _get_tuple_value(inferred: tuple) -> tuple[int, ...]:
        elts = inferred.elts
        return tuple(elt.value for elt in elts)

    def test_args(self) -> None:
        expected_values = [
            (),
            (1,),
            (2, 3),
            (4, 5),
            (3,),
            (),
            (3, 4, 5),
            (),
            (),
            (4,),
            (4, 5),
            (),
            (3,),
            (),
            (),
            (3,),
            (42,),
        ]
        ast_nodes = extract_node(
            """
        def func(*args):
            return args
        func() #@
        func(1) #@
        func(2, 3) #@
        func(*(4, 5)) #@
        def func(a, b, *args):
            return args
        func(1, 2, 3) #@
        func(1, 2) #@
        func(1, 2, 3, 4, 5) #@
        def func(a, b, c=42, *args):
            return args
        func(1, 2) #@
        func(1, 2, 3) #@
        func(1, 2, 3, 4) #@
        func(1, 2, 3, 4, 5) #@
        func = lambda a, b, *args: args
        func(1, 2) #@
        func(1, 2, 3) #@
        func = lambda a, b=42, *args: args
        func(1) #@
        func(1, 2) #@
        func(1, 2, 3) #@
        func(1, 2, *(42, )) #@
        """
        )
        for node, expected_value in zip(ast_nodes, expected_values):
            inferred = next(node.infer())
            self.assertIsInstance(inferred, nodes.Tuple)
            self.assertEqual(self._get_tuple_value(inferred), expected_value)

    def test_multiple_starred_args(self) -> None:
        expected_values = [(1, 2, 3), (1, 4, 2, 3, 5, 6, 7)]
        ast_nodes = extract_node(
            """
        def func(a, b, *args):
            return args
        func(1, 2, *(1, ), *(2, 3)) #@
        func(1, 2, *(1, ), 4, *(2, 3), 5, *(6, 7)) #@
        """
        )
        for node, expected_value in zip(ast_nodes, expected_values):
            inferred = next(node.infer())
            self.assertIsInstance(inferred, nodes.Tuple)
            self.assertEqual(self._get_tuple_value(inferred), expected_value)

    def test_defaults(self) -> None:
        expected_values = [42, 3, 41, 42]
        ast_nodes = extract_node(
            """
        def func(a, b, c=42, *args):
            return c
        func(1, 2) #@
        func(1, 2, 3) #@
        func(1, 2, c=41) #@
        func(1, 2, 42, 41) #@
        """
        )
        for node, expected_value in zip(ast_nodes, expected_values):
            inferred = next(node.infer())
            self.assertIsInstance(inferred, nodes.Const)
            self.assertEqual(inferred.value, expected_value)

    def test_kwonly_args(self) -> None:
        expected_values = [24, 24, 42, 23, 24, 24, 54]
        ast_nodes = extract_node(
            """
        def test(*, f, b): return f
        test(f=24, b=33) #@
        def test(a, *, f): return f
        test(1, f=24) #@
        def test(a, *, f=42): return f
        test(1) #@
        test(1, f=23) #@
        def test(a, b, c=42, *args, f=24):
            return f
        test(1, 2, 3) #@
        test(1, 2, 3, 4) #@
        test(1, 2, 3, 4, 5, f=54) #@
        """
        )
        for node, expected_value in zip(ast_nodes, expected_values):
            inferred = next(node.infer())
            self.assertIsInstance(inferred, nodes.Const)
            self.assertEqual(inferred.value, expected_value)

    def test_kwargs(self) -> None:
        expected = [[("a", 1), ("b", 2), ("c", 3)], [("a", 1)], [("a", "b")]]
        ast_nodes = extract_node(
            """
        def test(**kwargs):
             return kwargs
        test(a=1, b=2, c=3) #@
        test(a=1) #@
        test(**{'a': 'b'}) #@
        """
        )
        for node, expected_value in zip(ast_nodes, expected):
            inferred = next(node.infer())
            self.assertIsInstance(inferred, nodes.Dict)
            value = self._get_dict_value(inferred)
            self.assertEqual(value, expected_value)

    def test_kwargs_and_other_named_parameters(self) -> None:
        ast_nodes = extract_node(
            """
        def test(a=42, b=24, **kwargs):
            return kwargs
        test(42, 24, c=3, d=4) #@
        test(49, b=24, d=4) #@
        test(a=42, b=33, c=3, d=42) #@
        test(a=42, **{'c':42}) #@
        """
        )
        expected_values = [
            [("c", 3), ("d", 4)],
            [("d", 4)],
            [("c", 3), ("d", 42)],
            [("c", 42)],
        ]
        for node, expected_value in zip(ast_nodes, expected_values):
            inferred = next(node.infer())
            self.assertIsInstance(inferred, nodes.Dict)
            value = self._get_dict_value(inferred)
            self.assertEqual(value, expected_value)

    def test_kwargs_access_by_name(self) -> None:
        expected_values = [42, 42, 42, 24]
        ast_nodes = extract_node(
            """
        def test(**kwargs):
            return kwargs['f']
        test(f=42) #@
        test(**{'f': 42}) #@
        test(**dict(f=42)) #@
        def test(f=42, **kwargs):
            return kwargs['l']
        test(l=24) #@
        """
        )
        for ast_node, value in zip(ast_nodes, expected_values):
            inferred = next(ast_node.infer())
            self.assertIsInstance(inferred, nodes.Const, inferred)
            self.assertEqual(inferred.value, value)

    def test_multiple_kwargs(self) -> None:
        expected_value = [("a", 1), ("b", 2), ("c", 3), ("d", 4), ("f", 42)]
        ast_node = extract_node(
            """
        def test(**kwargs):
             return kwargs
        test(a=1, b=2, **{'c': 3}, **{'d': 4}, f=42) #@
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, nodes.Dict)
        value = self._get_dict_value(inferred)
        self.assertEqual(value, expected_value)

    def test_kwargs_are_overridden(self) -> None:
        ast_nodes = extract_node(
            """
        def test(f):
             return f
        test(f=23, **{'f': 34}) #@
        def test(f=None):
             return f
        test(f=23, **{'f':23}) #@
        """
        )
        for ast_node in ast_nodes:
            inferred = next(ast_node.infer())
            self.assertEqual(inferred, util.Uninferable)

    def test_fail_to_infer_args(self) -> None:
        ast_nodes = extract_node(
            """
        def test(a, **kwargs): return a
        test(*missing) #@
        test(*object) #@
        test(*1) #@


        def test(**kwargs): return kwargs
        test(**miss) #@
        test(**(1, 2)) #@
        test(**1) #@
        test(**{misss:1}) #@
        test(**{object:1}) #@
        test(**{1:1}) #@
        test(**{'a':1, 'a':1}) #@

        def test(a): return a
        test() #@
        test(1, 2, 3) #@

        from unknown import unknown
        test(*unknown) #@
        def test(*args): return args
        test(*unknown) #@
        """
        )
        for node in ast_nodes:
            inferred = next(node.infer())
            self.assertEqual(inferred, util.Uninferable)

    def test_args_overwritten(self) -> None:
        # https://github.com/pylint-dev/astroid/issues/180
        node = extract_node(
            """
        next = 42
        def wrapper(next=next):
             next = 24
             def test():
                 return next
             return test
        wrapper()() #@
        """
        )
        assert isinstance(node, nodes.NodeNG)
        inferred = node.inferred()
        self.assertEqual(len(inferred), 1)
        self.assertIsInstance(inferred[0], nodes.Const, inferred[0])
        self.assertEqual(inferred[0].value, 24)


class SliceTest(unittest.TestCase):
    def test_slice(self) -> None:
        ast_nodes = [
            ("[1, 2, 3][slice(None)]", [1, 2, 3]),
            ("[1, 2, 3][slice(None, None)]", [1, 2, 3]),
            ("[1, 2, 3][slice(None, None, None)]", [1, 2, 3]),
            ("[1, 2, 3][slice(1, None)]", [2, 3]),
            ("[1, 2, 3][slice(None, 1, None)]", [1]),
            ("[1, 2, 3][slice(0, 1)]", [1]),
            ("[1, 2, 3][slice(0, 3, 2)]", [1, 3]),
        ]
        for node, expected_value in ast_nodes:
            ast_node = extract_node(f"__({node})")
            inferred = next(ast_node.infer())
            self.assertIsInstance(inferred, nodes.List)
            self.assertEqual([elt.value for elt in inferred.elts], expected_value)

    def test_slice_inference_error(self) -> None:
        ast_nodes = extract_node(
            """
        from unknown import unknown
        [1, 2, 3][slice(None, unknown, unknown)] #@
        [1, 2, 3][slice(None, missing, missing)] #@
        [1, 2, 3][slice(object, list, tuple)] #@
        [1, 2, 3][slice(b'a')] #@
        [1, 2, 3][slice(1, 'aa')] #@
        [1, 2, 3][slice(1, 2.0, 3.0)] #@
        [1, 2, 3][slice()] #@
        [1, 2, 3][slice(1, 2, 3, 4)] #@
        """
        )
        for node in ast_nodes:
            self.assertRaises(InferenceError, next, node.infer())

    def test_slice_attributes(self) -> None:
        ast_nodes = [
            ("slice(2, 3, 4)", (2, 3, 4)),
            ("slice(None, None, 4)", (None, None, 4)),
            ("slice(None, 1, None)", (None, 1, None)),
        ]
        for code, values in ast_nodes:
            lower, upper, step = values
            node = extract_node(code)
            inferred = next(node.infer())
            self.assertIsInstance(inferred, nodes.Slice)
            lower_value = next(inferred.igetattr("start"))
            self.assertIsInstance(lower_value, nodes.Const)
            self.assertEqual(lower_value.value, lower)
            higher_value = next(inferred.igetattr("stop"))
            self.assertIsInstance(higher_value, nodes.Const)
            self.assertEqual(higher_value.value, upper)
            step_value = next(inferred.igetattr("step"))
            self.assertIsInstance(step_value, nodes.Const)
            self.assertEqual(step_value.value, step)
            self.assertEqual(inferred.pytype(), "builtins.slice")

    def test_slice_type(self) -> None:
        ast_node = extract_node("type(slice(None, None, None))")
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, nodes.ClassDef)
        self.assertEqual(inferred.name, "slice")


class CallSiteTest(unittest.TestCase):
    @staticmethod
    def _call_site_from_call(call: nodes.Call) -> CallSite:
        return arguments.CallSite.from_call(call)

    def _test_call_site_pair(
        self, code: str, expected_args: list[int], expected_keywords: dict[str, int]
    ) -> None:
        ast_node = extract_node(code)
        call_site = self._call_site_from_call(ast_node)
        self.assertEqual(len(call_site.positional_arguments), len(expected_args))
        self.assertEqual(
            [arg.value for arg in call_site.positional_arguments], expected_args
        )
        self.assertEqual(len(call_site.keyword_arguments), len(expected_keywords))
        for keyword, value in expected_keywords.items():
            self.assertIn(keyword, call_site.keyword_arguments)
            self.assertEqual(call_site.keyword_arguments[keyword].value, value)

    def _test_call_site(
        self, pairs: list[tuple[str, list[int], dict[str, int]]]
    ) -> None:
        for pair in pairs:
            self._test_call_site_pair(*pair)

    def test_call_site_starred_args(self) -> None:
        pairs = [
            (
                "f(*(1, 2), *(2, 3), *(3, 4), **{'a':1}, **{'b': 2})",
                [1, 2, 2, 3, 3, 4],
                {"a": 1, "b": 2},
            ),
            (
                "f(1, 2, *(3, 4), 5, *(6, 7), f=24, **{'c':3})",
                [1, 2, 3, 4, 5, 6, 7],
                {"f": 24, "c": 3},
            ),
            # Too many fs passed into.
            ("f(f=24, **{'f':24})", [], {}),
        ]
        self._test_call_site(pairs)

    def test_call_site(self) -> None:
        pairs = [
            ("f(1, 2)", [1, 2], {}),
            ("f(1, 2, *(1, 2))", [1, 2, 1, 2], {}),
            ("f(a=1, b=2, c=3)", [], {"a": 1, "b": 2, "c": 3}),
        ]
        self._test_call_site(pairs)

    def _test_call_site_valid_arguments(self, values: list[str], invalid: bool) -> None:
        for value in values:
            ast_node = extract_node(value)
            call_site = self._call_site_from_call(ast_node)
            self.assertEqual(call_site.has_invalid_arguments(), invalid)

    def test_call_site_valid_arguments(self) -> None:
        values = ["f(*lala)", "f(*1)", "f(*object)"]
        self._test_call_site_valid_arguments(values, invalid=True)
        values = ["f()", "f(*(1, ))", "f(1, 2, *(2, 3))"]
        self._test_call_site_valid_arguments(values, invalid=False)

    def test_duplicated_keyword_arguments(self) -> None:
        ast_node = extract_node('f(f=24, **{"f": 25})')
        site = self._call_site_from_call(ast_node)
        self.assertIn("f", site.duplicated_keywords)

    def test_call_site_uninferable(self) -> None:
        code = """
            def get_nums():
                nums = ()
                if x == '1':
                    nums = (1, 2)
                return nums

            def add(x, y):
                return x + y

            nums = get_nums()

            if x:
                kwargs = {1: bar}
            else:
                kwargs = {}

            if nums:
                add(*nums)
                print(**kwargs)
        """
        # Test that `*nums` argument should be Uninferable
        ast = parse(code, __name__)
        *_, add_call, print_call = list(ast.nodes_of_class(nodes.Call))
        nums_arg = add_call.args[0]
        add_call_site = self._call_site_from_call(add_call)
        self.assertEqual(add_call_site._unpack_args([nums_arg]), [Uninferable])

        print_call_site = self._call_site_from_call(print_call)
        keywords = CallContext(print_call.args, print_call.keywords).keywords
        self.assertEqual(
            print_call_site._unpack_keywords(keywords), {None: Uninferable}
        )


class ObjectDunderNewTest(unittest.TestCase):
    def test_object_dunder_new_is_inferred_if_decorator(self) -> None:
        node = extract_node(
            """
        @object.__new__
        class instance(object):
            pass
        """
        )
        inferred = next(node.infer())
        self.assertIsInstance(inferred, Instance)


@pytest.mark.parametrize(
    "code, result",
    [
        # regular f-string
        (
            """width = 10
precision = 4
value = 12.34567
result = f"result: {value:{width}.{precision}}!"
""",
            "result:      12.35!",
        ),
        # unsupported format
        (
            """width = None
precision = 4
value = 12.34567
result = f"result: {value:{width}.{precision}}!"
""",
            None,
        ),
        # unsupported value
        (
            """width = 10
precision = 4
value = None
result = f"result: {value:{width}.{precision}}!"
""",
            None,
        ),
    ],
)
def test_formatted_fstring_inference(code, result) -> None:
    ast = parse(code, __name__)
    node = ast["result"]
    inferred = node.inferred()
    assert len(inferred) == 1
    value_node = inferred[0]
    if result is None:
        assert value_node is util.Uninferable
    else:
        assert isinstance(value_node, Const)
        assert value_node.value == result


def test_augassign_recursion() -> None:
    """Make sure inference doesn't throw a RecursionError.

    Regression test for augmented assign dropping context.path
    causing recursion errors
    """
    # infinitely recurses in python
    code = """
    def rec():
        a = 0
        a += rec()
        return a
    rec()
    """
    cls_node = extract_node(code)
    assert next(cls_node.infer()) is util.Uninferable


def test_infer_custom_inherit_from_property() -> None:
    node = extract_node(
        """
    class custom_property(property):
        pass

    class MyClass(object):
        @custom_property
        def my_prop(self):
            return 1

    MyClass().my_prop
    """
    )
    inferred = next(node.infer())
    assert isinstance(inferred, nodes.Const)
    assert inferred.value == 1


def test_cannot_infer_call_result_for_builtin_methods() -> None:
    node = extract_node(
        """
    a = "fast"
    a
    """
    )
    inferred = next(node.infer())
    lenmeth = next(inferred.igetattr("__len__"))
    with pytest.raises(InferenceError):
        next(lenmeth.infer_call_result(None, None))


def test_unpack_dicts_in_assignment() -> None:
    ast_nodes = extract_node(
        """
    a, b = {1:2, 2:3}
    a #@
    b #@
    """
    )
    assert isinstance(ast_nodes, list)
    first_inferred = next(ast_nodes[0].infer())
    second_inferred = next(ast_nodes[1].infer())
    assert isinstance(first_inferred, nodes.Const)
    assert first_inferred.value == 1
    assert isinstance(second_inferred, nodes.Const)
    assert second_inferred.value == 2


def test_slice_inference_in_for_loops() -> None:
    node = extract_node(
        """
    for a, (c, *b) in [(1, (2, 3, 4)), (4, (5, 6))]:
       b #@
    """
    )
    inferred = next(node.infer())
    assert isinstance(inferred, nodes.List)
    assert inferred.as_string() == "[3, 4]"

    node = extract_node(
        """
    for a, *b in [(1, 2, 3, 4)]:
       b #@
    """
    )
    inferred = next(node.infer())
    assert isinstance(inferred, nodes.List)
    assert inferred.as_string() == "[2, 3, 4]"

    node = extract_node(
        """
    for a, *b in [(1,)]:
       b #@
    """
    )
    inferred = next(node.infer())
    assert isinstance(inferred, nodes.List)
    assert inferred.as_string() == "[]"


def test_slice_inference_in_for_loops_not_working() -> None:
    ast_nodes = extract_node(
        """
    from unknown import Unknown
    for a, *b in something:
        b #@
    for a, *b in Unknown:
        b #@
    for a, *b in (1):
        b #@
    """
    )
    for node in ast_nodes:
        inferred = next(node.infer())
        assert inferred == util.Uninferable


def test_slice_zero_step_does_not_raise_ValueError() -> None:
    node = extract_node("x = [][::0]; x")
    assert next(node.infer()) == util.Uninferable


def test_slice_zero_step_on_str_does_not_raise_ValueError() -> None:
    node = extract_node('x = ""[::0]; x')
    assert next(node.infer()) == util.Uninferable


def test_unpacking_starred_and_dicts_in_assignment() -> None:
    node = extract_node(
        """
    a, *b = {1:2, 2:3, 3:4}
    b
    """
    )
    inferred = next(node.infer())
    assert isinstance(inferred, nodes.List)
    assert inferred.as_string() == "[2, 3]"

    node = extract_node(
        """
    a, *b = {1:2}
    b
    """
    )
    inferred = next(node.infer())
    assert isinstance(inferred, nodes.List)
    assert inferred.as_string() == "[]"


def test_unpacking_starred_empty_list_in_assignment() -> None:
    node = extract_node(
        """
    a, *b, c = [1, 2]
    b #@
    """
    )
    inferred = next(node.infer())
    assert isinstance(inferred, nodes.List)
    assert inferred.as_string() == "[]"


def test_regression_infinite_loop_decorator() -> None:
    """Make sure decorators with the same names
    as a decorated method do not cause an infinite loop.

    See https://github.com/pylint-dev/astroid/issues/375
    """
    code = """
    from functools import lru_cache

    class Foo():
        @lru_cache()
        def lru_cache(self, value):
            print('Computing {}'.format(value))
            return value
    Foo().lru_cache(1)
    """
    node = extract_node(code)
    assert isinstance(node, nodes.NodeNG)
    [result] = node.inferred()
    assert result.value == 1


def test_stop_iteration_in_int() -> None:
    """Handle StopIteration error in infer_int."""
    code = """
    def f(lst):
        if lst[0]:
            return f(lst)
        else:
            args = lst[:1]
            return int(args[0])

    f([])
    """
    [first_result, second_result] = extract_node(code).inferred()
    assert first_result is util.Uninferable
    assert isinstance(second_result, Instance)
    assert second_result.name == "int"


def test_call_on_instance_with_inherited_dunder_call_method() -> None:
    """Stop inherited __call__ method from incorrectly returning wrong class.

    See https://github.com/pylint-dev/pylint/issues/2199
    """
    node = extract_node(
        """
    class Base:
        def __call__(self):
            return self

    class Sub(Base):
        pass
    obj = Sub()
    val = obj()
    val #@
    """
    )
    assert isinstance(node, nodes.NodeNG)
    [val] = node.inferred()
    assert isinstance(val, Instance)
    assert val.name == "Sub"


class TestInferencePropagation:
    """Make sure function argument values are properly
    propagated to sub functions.
    """

    @pytest.mark.xfail(reason="Relying on path copy")
    def test_call_context_propagation(self):
        n = extract_node(
            """
        def chest(a):
            return a * a
        def best(a, b):
            return chest(a)
        def test(a, b, c):
            return best(a, b)
        test(4, 5, 6) #@
        """
        )
        assert next(n.infer()).as_string() == "16"

    def test_call_starargs_propagation(self) -> None:
        code = """
        def foo(*args):
            return args
        def bar(*args):
            return foo(*args)
        bar(4, 5, 6, 7) #@
        """
        assert next(extract_node(code).infer()).as_string() == "(4, 5, 6, 7)"

    def test_call_kwargs_propagation(self) -> None:
        code = """
        def b(**kwargs):
            return kwargs
        def f(**kwargs):
            return b(**kwargs)
        f(**{'f': 1}) #@
        """
        assert next(extract_node(code).infer()).as_string() == "{'f': 1}"


@pytest.mark.parametrize(
    "op,result",
    [
        ("<", False),
        ("<=", True),
        ("==", True),
        (">=", True),
        (">", False),
        ("!=", False),
    ],
)
def test_compare(op, result) -> None:
    code = f"""
    123 {op} 123
    """
    node = extract_node(code)
    inferred = next(node.infer())
    assert inferred.value == result


@pytest.mark.xfail(reason="uninferable")
@pytest.mark.parametrize(
    "op,result",
    [
        ("is", True),
        ("is not", False),
    ],
)
def test_compare_identity(op, result) -> None:
    code = f"""
    obj = object()
    obj {op} obj
    """
    node = extract_node(code)
    inferred = next(node.infer())
    assert inferred.value == result


@pytest.mark.parametrize(
    "op,result",
    [
        ("in", True),
        ("not in", False),
    ],
)
def test_compare_membership(op, result) -> None:
    code = f"""
    1 {op} [1, 2, 3]
    """
    node = extract_node(code)
    inferred = next(node.infer())
    assert inferred.value == result


@pytest.mark.parametrize(
    "lhs,rhs,result",
    [
        (1, 1, True),
        (1, 1.1, True),
        (1.1, 1, False),
        (1.0, 1.0, True),
        ("abc", "def", True),
        ("abc", "", False),
        ([], [1], True),
        ((1, 2), (2, 3), True),
        ((1, 0), (1,), False),
        (True, True, True),
        (True, False, False),
        (False, 1, True),
        (1 + 0j, 2 + 0j, util.Uninferable),
        (+0.0, -0.0, True),
        (0, "1", util.Uninferable),
        (b"\x00", b"\x01", True),
    ],
)
def test_compare_lesseq_types(lhs, rhs, result) -> None:
    code = f"""
    {lhs!r} <= {rhs!r}
    """
    node = extract_node(code)
    inferred = next(node.infer())
    assert inferred.value == result


def test_compare_chained() -> None:
    code = """
    3 < 5 > 3
    """
    node = extract_node(code)
    inferred = next(node.infer())
    assert inferred.value is True


def test_compare_inferred_members() -> None:
    code = """
    a = 11
    b = 13
    a < b
    """
    node = extract_node(code)
    inferred = next(node.infer())
    assert inferred.value is True


def test_compare_instance_members() -> None:
    code = """
    class A:
        value = 123
    class B:
        @property
        def value(self):
            return 456
    A().value < B().value
    """
    node = extract_node(code)
    inferred = next(node.infer())
    assert inferred.value is True


@pytest.mark.xfail(reason="unimplemented")
def test_compare_dynamic() -> None:
    code = """
    class A:
        def __le__(self, other):
            return True
    A() <= None
    """
    node = extract_node(code)
    inferred = next(node.infer())
    assert inferred.value is True


def test_compare_uninferable_member() -> None:
    code = """
    from unknown import UNKNOWN
    0 <= UNKNOWN
    """
    node = extract_node(code)
    inferred = next(node.infer())
    assert inferred is util.Uninferable


def test_compare_chained_comparisons_shortcircuit_on_false() -> None:
    code = """
    from unknown import UNKNOWN
    2 < 1 < UNKNOWN
    """
    node = extract_node(code)
    inferred = next(node.infer())
    assert inferred.value is False


def test_compare_chained_comparisons_continue_on_true() -> None:
    code = """
    from unknown import UNKNOWN
    1 < 2 < UNKNOWN
    """
    node = extract_node(code)
    inferred = next(node.infer())
    assert inferred is util.Uninferable


@pytest.mark.xfail(reason="unimplemented")
def test_compare_known_false_branch() -> None:
    code = """
    a = 'hello'
    if 1 < 2:
        a = 'goodbye'
    a
    """
    node = extract_node(code)
    inferred = list(node.infer())
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == "hello"


def test_compare_ifexp_constant() -> None:
    code = """
    a = 'hello' if 1 < 2 else 'goodbye'
    a
    """
    node = extract_node(code)
    inferred = list(node.infer())
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == "hello"


def test_compare_typeerror() -> None:
    code = """
    123 <= "abc"
    """
    node = extract_node(code)
    inferred = list(node.infer())
    assert len(inferred) == 1
    assert inferred[0] is util.Uninferable


def test_compare_multiple_possibilites() -> None:
    code = """
    from unknown import UNKNOWN
    a = 1
    if UNKNOWN:
        a = 2
    b = 3
    if UNKNOWN:
        b = 4
    a < b
    """
    node = extract_node(code)
    inferred = list(node.infer())
    assert len(inferred) == 1
    # All possible combinations are true: (1 < 3), (1 < 4), (2 < 3), (2 < 4)
    assert inferred[0].value is True


def test_compare_ambiguous_multiple_possibilites() -> None:
    code = """
    from unknown import UNKNOWN
    a = 1
    if UNKNOWN:
        a = 3
    b = 2
    if UNKNOWN:
        b = 4
    a < b
    """
    node = extract_node(code)
    inferred = list(node.infer())
    assert len(inferred) == 1
    # Not all possible combinations are true: (1 < 2), (1 < 4), (3 !< 2), (3 < 4)
    assert inferred[0] is util.Uninferable


def test_compare_nonliteral() -> None:
    code = """
    def func(a, b):
        return (a, b) <= (1, 2) #@
    """
    return_node = extract_node(code)
    node = return_node.value
    inferred = list(node.infer())  # should not raise ValueError
    assert len(inferred) == 1
    assert inferred[0] is util.Uninferable


def test_compare_unknown() -> None:
    code = """
    def func(a):
        if tuple() + (a[1],) in set():
            raise Exception()
    """
    node = extract_node(code)
    inferred = list(node.infer())
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.FunctionDef)


def test_limit_inference_result_amount() -> None:
    """Test setting limit inference result amount."""
    code = """
    args = []

    if True:
        args += ['a']

    if True:
        args += ['b']

    if True:
        args += ['c']

    if True:
        args += ['d']

    args #@
    """
    result = extract_node(code).inferred()
    assert len(result) == 16
    with patch("astroid.manager.AstroidManager.max_inferable_values", 4):
        result_limited = extract_node(code).inferred()
    # Can't guarantee exact size
    assert len(result_limited) < 16
    # Will not always be at the end
    assert util.Uninferable in result_limited


def test_attribute_inference_should_not_access_base_classes() -> None:
    """Attributes of classes should mask ancestor attributes."""
    code = """
    type.__new__ #@
    """
    res = extract_node(code).inferred()
    assert len(res) == 1
    assert res[0].parent.name == "type"


def test_attribute_mro_object_inference() -> None:
    """Inference should only infer results from the first available method."""
    inferred = extract_node(
        """
    class A:
        def foo(self):
            return 1
    class B(A):
        def foo(self):
            return 2
    B().foo() #@
    """
    ).inferred()
    assert len(inferred) == 1
    assert inferred[0].value == 2


def test_inferred_sequence_unpacking_works() -> None:
    inferred = next(
        extract_node(
            """
    def test(*args):
        return (1, *args)
    test(2) #@
    """
        ).infer()
    )
    assert isinstance(inferred, nodes.Tuple)
    assert len(inferred.elts) == 2
    assert [value.value for value in inferred.elts] == [1, 2]


def test_recursion_error_inferring_slice() -> None:
    node = extract_node(
        """
    class MyClass:
        def __init__(self):
            self._slice = slice(0, 10)

        def incr(self):
            self._slice = slice(0, self._slice.stop + 1)

        def test(self):
            self._slice #@
    """
    )
    inferred = next(node.infer())
    assert isinstance(inferred, Slice)


def test_exception_lookup_last_except_handler_wins() -> None:
    node = extract_node(
        """
    try:
        1/0
    except ValueError as exc:
        pass
    try:
        1/0
    except OSError as exc:
        exc #@
    """
    )
    assert isinstance(node, nodes.NodeNG)
    inferred = node.inferred()
    assert len(inferred) == 1
    inferred_exc = inferred[0]
    assert isinstance(inferred_exc, Instance)
    assert inferred_exc.name == "OSError"

    # Two except handlers on the same Try work the same as separate
    node = extract_node(
        """
    try:
        1/0
    except ZeroDivisionError as exc:
        pass
    except ValueError as exc:
        exc #@
    """
    )
    assert isinstance(node, nodes.NodeNG)
    inferred = node.inferred()
    assert len(inferred) == 1
    inferred_exc = inferred[0]
    assert isinstance(inferred_exc, Instance)
    assert inferred_exc.name == "ValueError"


def test_exception_lookup_name_bound_in_except_handler() -> None:
    node = extract_node(
        """
    try:
        1/0
    except ValueError:
        name = 1
    try:
        1/0
    except OSError:
        name = 2
        name #@
    """
    )
    assert isinstance(node, nodes.NodeNG)
    inferred = node.inferred()
    assert len(inferred) == 1
    inferred_exc = inferred[0]
    assert isinstance(inferred_exc, nodes.Const)
    assert inferred_exc.value == 2


def test_builtin_inference_list_of_exceptions() -> None:
    node = extract_node(
        """
    tuple([ValueError, TypeError])
    """
    )
    inferred = next(node.infer())
    assert isinstance(inferred, nodes.Tuple)
    assert len(inferred.elts) == 2
    assert isinstance(inferred.elts[0], nodes.EvaluatedObject)
    assert isinstance(inferred.elts[0].value, nodes.ClassDef)
    assert inferred.elts[0].value.name == "ValueError"
    assert isinstance(inferred.elts[1], nodes.EvaluatedObject)
    assert isinstance(inferred.elts[1].value, nodes.ClassDef)
    assert inferred.elts[1].value.name == "TypeError"

    # Test that inference of evaluated objects returns what is expected
    first_elem = next(inferred.elts[0].infer())
    assert isinstance(first_elem, nodes.ClassDef)
    assert first_elem.name == "ValueError"

    second_elem = next(inferred.elts[1].infer())
    assert isinstance(second_elem, nodes.ClassDef)
    assert second_elem.name == "TypeError"

    # Test that as_string() also works
    as_string = inferred.as_string()
    assert as_string.strip() == "(ValueError, TypeError)"


def test_cannot_getattr_ann_assigns() -> None:
    node = extract_node(
        """
    class Cls:
        ann: int
    """
    )
    inferred = next(node.infer())
    with pytest.raises(AttributeInferenceError):
        inferred.getattr("ann")

    # But if it had a value, then it would be okay.
    node = extract_node(
        """
    class Cls:
        ann: int = 0
    """
    )
    inferred = next(node.infer())
    values = inferred.getattr("ann")
    assert len(values) == 1


def test_prevent_recursion_error_in_igetattr_and_context_manager_inference() -> None:
    code = """
    class DummyContext(object):
        def __enter__(self):
            return self
        def __exit__(self, ex_type, ex_value, ex_tb):
            return True

    if False:
        with DummyContext() as con:
            pass

    with DummyContext() as con:
        con.__enter__  #@
    """
    node = extract_node(code)
    # According to the original issue raised that introduced this test
    # (https://github.com/pylint-dev/astroid/663, see 55076ca), this test was a
    # non-regression check for StopIteration leaking out of inference and
    # causing a RuntimeError. Hence, here just consume the inferred value
    # without checking it and rely on pytest to fail on raise
    next(node.infer())


def test_igetattr_idempotent() -> None:
    code = """
    class InferMeTwice:
        item = 10

    InferMeTwice()
    """
    call = extract_node(code)
    instance = call.inferred()[0]
    context_to_be_used_twice = InferenceContext()
    assert util.Uninferable not in instance.igetattr("item", context_to_be_used_twice)
    assert util.Uninferable not in instance.igetattr("item", context_to_be_used_twice)


@patch("astroid.nodes.Call._infer")
def test_cache_usage_without_explicit_context(mock) -> None:
    code = """
    class InferMeTwice:
        item = 10

    InferMeTwice()
    """
    call = extract_node(code)
    mock.return_value = [Uninferable]

    # no explicit InferenceContext
    call.inferred()
    call.inferred()

    mock.assert_called_once()


def test_infer_context_manager_with_unknown_args() -> None:
    code = """
    class client_log(object):
        def __init__(self, client):
            self.client = client
        def __enter__(self):
            return self.client
        def __exit__(self, exc_type, exc_value, traceback):
            pass

    with client_log(None) as c:
        c #@
    """
    node = extract_node(code)
    assert next(node.infer()) is util.Uninferable

    # But if we know the argument, then it is easy
    code = """
    class client_log(object):
        def __init__(self, client=24):
            self.client = client
        def __enter__(self):
            return self.client
        def __exit__(self, exc_type, exc_value, traceback):
            pass

    with client_log(None) as c:
        c #@
    """
    node = extract_node(code)
    assert isinstance(next(node.infer()), nodes.Const)


@pytest.mark.parametrize(
    "code",
    [
        """
        class Error(Exception):
            pass

        a = Error()
        a #@
        """,
        """
        class Error(Exception):
            def method(self):
                 self #@
        """,
    ],
)
def test_subclass_of_exception(code) -> None:
    inferred = next(extract_node(code).infer())
    assert isinstance(inferred, Instance)
    args = next(inferred.igetattr("args"))
    assert isinstance(args, nodes.Tuple)


def test_ifexp_inference() -> None:
    code = """
    def truth_branch():
        return 1 if True else 2

    def false_branch():
        return 1 if False else 2

    def both_branches():
        return 1 if unknown() else 2

    truth_branch() #@
    false_branch() #@
    both_branches() #@
    """
    ast_nodes = extract_node(code)
    assert isinstance(ast_nodes, list)
    first = next(ast_nodes[0].infer())
    assert isinstance(first, nodes.Const)
    assert first.value == 1

    second = next(ast_nodes[1].infer())
    assert isinstance(second, nodes.Const)
    assert second.value == 2

    third = list(ast_nodes[2].infer())
    assert isinstance(third, list)
    assert [third[0].value, third[1].value] == [1, 2]


def test_assert_last_function_returns_none_on_inference() -> None:
    code = """
    def check_equal(a, b):
        res = do_something_with_these(a, b)
        assert a == b == res

    check_equal(a, b)
    """
    node = extract_node(code)
    inferred = next(node.infer())
    assert isinstance(inferred, nodes.Const)
    assert inferred.value is None


def test_posonlyargs_inference() -> None:
    code = """
    class A:
        method = lambda self, b, /, c: b + c

        def __init__(self, other=(), /, **kw):
            self #@
    A() #@
    A().method #@

    """
    self_node, instance, lambda_method = extract_node(code)
    inferred = next(self_node.infer())
    assert isinstance(inferred, Instance)
    assert inferred.name == "A"

    inferred = next(instance.infer())
    assert isinstance(inferred, Instance)
    assert inferred.name == "A"

    inferred = next(lambda_method.infer())
    assert isinstance(inferred, BoundMethod)
    assert inferred.type == "method"


def test_infer_args_unpacking_of_self() -> None:
    code = """
    class A:
        def __init__(*args, **kwargs):
            self, *args = args
            self.data = {1: 2}
            self #@
    A().data #@
    """
    self, data = extract_node(code)
    inferred_self = next(self.infer())
    assert isinstance(inferred_self, Instance)
    assert inferred_self.name == "A"

    inferred_data = next(data.infer())
    assert isinstance(inferred_data, nodes.Dict)
    assert inferred_data.as_string() == "{1: 2}"


def test_infer_exception_instance_attributes() -> None:
    code = """
    class UnsupportedFormatCharacter(Exception):
        def __init__(self, index):
            Exception.__init__(self, index)
            self.index = index

    try:
       1/0
    except UnsupportedFormatCharacter as exc:
       exc #@
    """
    node = extract_node(code)
    inferred = next(node.infer())
    assert isinstance(inferred, ExceptionInstance)
    index = inferred.getattr("index")
    assert len(index) == 1
    assert isinstance(index[0], nodes.AssignAttr)


def test_infer_assign_attr() -> None:
    code = """
    class Counter:
        def __init__(self):
            self.count = 0

        def increment(self):
            self.count += 1  #@
    """
    node = extract_node(code)
    inferred = next(node.infer())
    assert inferred.value == 1


@pytest.mark.parametrize(
    "code,instance_name",
    [
        (
            """
        class A:
            def __enter__(self):
                return self
            def __exit__(self, err_type, err, traceback):
                return
        class B(A):
            pass
        with B() as b:
            b #@
        """,
            "B",
        ),
        (
            """
    class A:
        def __enter__(self):
            return A()
        def __exit__(self, err_type, err, traceback):
            return
    class B(A):
            pass
    with B() as b:
        b #@
    """,
            "A",
        ),
        (
            """
        class A:
            def test(self):
                return A()
        class B(A):
            def test(self):
                return A.test(self)
        B().test()
        """,
            "A",
        ),
    ],
)
def test_inference_is_limited_to_the_boundnode(code, instance_name) -> None:
    node = extract_node(code)
    inferred = next(node.infer())
    assert isinstance(inferred, Instance)
    assert inferred.name == instance_name


def test_property_inference() -> None:
    code = """
    class A:
        @property
        def test(self):
            return 42

        @test.setter
        def test(self, value):
            return "banco"

    A.test #@
    A().test #@
    A.test.fget(A) #@
    A.test.fset(A, "a_value") #@
    A.test.setter #@
    A.test.getter #@
    A.test.deleter #@
    """
    (
        prop,
        prop_result,
        prop_fget_result,
        prop_fset_result,
        prop_setter,
        prop_getter,
        prop_deleter,
    ) = extract_node(code)

    inferred = next(prop.infer())
    assert isinstance(inferred, objects.Property)
    assert inferred.pytype() == "builtins.property"
    assert inferred.type == "property"

    inferred = next(prop_result.infer())
    assert isinstance(inferred, nodes.Const)
    assert inferred.value == 42

    inferred = next(prop_fget_result.infer())
    assert isinstance(inferred, nodes.Const)
    assert inferred.value == 42

    inferred = next(prop_fset_result.infer())
    assert isinstance(inferred, nodes.Const)
    assert inferred.value == "banco"

    for prop_func in prop_setter, prop_getter, prop_deleter:
        inferred = next(prop_func.infer())
        assert isinstance(inferred, nodes.FunctionDef)


def test_property_as_string() -> None:
    code = """
    class A:
        @property
        def test(self):
            return 42

    A.test #@
    """
    node = extract_node(code)
    inferred = next(node.infer())
    assert isinstance(inferred, objects.Property)
    property_body = textwrap.dedent(
        """
    @property
    def test(self):
        return 42
    """
    )
    assert inferred.as_string().strip() == property_body.strip()


def test_property_callable_inference() -> None:
    code = """
    class A:
        def func(self):
            return 42
        p = property(func)
    A().p
    """
    property_call = extract_node(code)
    inferred = next(property_call.infer())
    assert isinstance(inferred, nodes.Const)
    assert inferred.value == 42

    # Try with lambda as well
    code = """
    class A:
        p = property(lambda self: 42)
    A().p
    """
    property_call = extract_node(code)
    inferred = next(property_call.infer())
    assert isinstance(inferred, nodes.Const)
    assert inferred.value == 42


def test_property_docstring() -> None:
    code = """
    class A:
        @property
        def test(self):
            '''Docstring'''
            return 42

    A.test #@
    """
    node = extract_node(code)
    inferred = next(node.infer())
    assert isinstance(inferred, objects.Property)
    assert isinstance(inferred.doc_node, nodes.Const)
    assert inferred.doc_node.value == "Docstring"


def test_recursion_error_inferring_builtin_containers() -> None:
    node = extract_node(
        """
    class Foo:
        a = "foo"
    inst = Foo()

    b = tuple([inst.a]) #@
    inst.a = b
    """
    )
    util.safe_infer(node.targets[0])


def test_inferaugassign_picking_parent_instead_of_stmt() -> None:
    code = """
    from collections import namedtuple
    SomeClass = namedtuple('SomeClass', ['name'])
    items = [SomeClass(name='some name')]

    some_str = ''
    some_str += ', '.join(__(item) for item in items)
    """
    # item needs to be inferrd as `SomeClass` but it was inferred
    # as a string because the entire `AugAssign` node was inferred
    # as a string.
    node = extract_node(code)
    inferred = next(node.infer())
    assert isinstance(inferred, Instance)
    assert inferred.name == "SomeClass"


def test_classmethod_from_builtins_inferred_as_bound() -> None:
    code = """
    import builtins

    class Foo():
        @classmethod
        def bar1(cls, text):
            pass

        @builtins.classmethod
        def bar2(cls, text):
            pass

    Foo.bar1 #@
    Foo.bar2 #@
    """
    first_node, second_node = extract_node(code)
    assert isinstance(next(first_node.infer()), BoundMethod)
    assert isinstance(next(second_node.infer()), BoundMethod)


def test_infer_dict_passes_context() -> None:
    code = """
    k = {}
    (_ for k in __(dict(**k)))
    """
    node = extract_node(code)
    inferred = next(node.infer())
    assert isinstance(inferred, Instance)
    assert inferred.qname() == "builtins.dict"


@pytest.mark.parametrize(
    "code,obj,obj_type",
    [
        (
            """
            def klassmethod1(method):
                @classmethod
                def inner(cls):
                    return method(cls)
                return inner

            class X(object):
                @klassmethod1
                def x(cls):
                    return 'X'
            X.x
            """,
            BoundMethod,
            "classmethod",
        ),
        (
            """
            def staticmethod1(method):
                @staticmethod
                def inner(cls):
                    return method(cls)
                return inner

            class X(object):
                @staticmethod1
                def x(cls):
                    return 'X'
            X.x
            """,
            nodes.FunctionDef,
            "staticmethod",
        ),
        (
            """
            def klassmethod1(method):
                def inner(cls):
                    return method(cls)
                return classmethod(inner)

            class X(object):
                @klassmethod1
                def x(cls):
                    return 'X'
            X.x
            """,
            BoundMethod,
            "classmethod",
        ),
        (
            """
            def staticmethod1(method):
                def inner(cls):
                    return method(cls)
                return staticmethod(inner)

            class X(object):
                @staticmethod1
                def x(cls):
                    return 'X'
            X.x
            """,
            nodes.FunctionDef,
            "staticmethod",
        ),
    ],
)
def test_custom_decorators_for_classmethod_and_staticmethods(code, obj, obj_type):
    node = extract_node(code)
    inferred = next(node.infer())
    assert isinstance(inferred, obj)
    assert inferred.type == obj_type


def test_dataclasses_subscript_inference_recursion_error_39():
    code = """
    from dataclasses import dataclass, replace

    @dataclass
    class ProxyConfig:
        auth: str = "/auth"


    a = ProxyConfig("")
    test_dict = {"proxy" : {"auth" : "", "bla" : "f"}}

    foo = test_dict['proxy']
    replace(a, **test_dict['proxy']) # This fails
    """
    node = extract_node(code)
    infer_val = util.safe_infer(node)
    assert isinstance(infer_val, Instance)
    assert infer_val.pytype() == ".ProxyConfig"


def test_self_reference_infer_does_not_trigger_recursion_error() -> None:
    # Prevents https://github.com/pylint-dev/pylint/issues/1285
    code = """
    def func(elems):
        return elems

    class BaseModel(object):

        def __init__(self, *args, **kwargs):
            self._reference = func(*self._reference.split('.'))
    BaseModel()._reference
    """
    node = extract_node(code)
    inferred = next(node.infer())
    assert inferred is util.Uninferable


def test_inferring_properties_multiple_time_does_not_mutate_locals() -> None:
    code = """
    class A:
        @property
        def a(self):
            return 42

    A()
    """
    node = extract_node(code)
    # Infer the class
    cls = next(node.infer())
    (prop,) = cls.getattr("a")

    # Try to infer the property function *multiple* times. `A.locals` should be modified only once
    for _ in range(3):
        prop.inferred()
    a_locals = cls.locals["a"]
    # [FunctionDef, Property]
    assert len(a_locals) == 2


def test_getattr_fails_on_empty_values() -> None:
    code = """
    import collections
    collections
    """
    node = extract_node(code)
    inferred = next(node.infer())
    with pytest.raises(InferenceError):
        next(inferred.igetattr(""))

    with pytest.raises(AttributeInferenceError):
        inferred.getattr("")


def test_infer_first_argument_of_static_method_in_metaclass() -> None:
    code = """
    class My(type):
        @staticmethod
        def test(args):
            args #@
    """
    node = extract_node(code)
    inferred = next(node.infer())
    assert inferred is util.Uninferable


def test_recursion_error_metaclass_monkeypatching() -> None:
    module = resources.build_file(
        "data/metaclass_recursion/monkeypatch.py", "data.metaclass_recursion"
    )
    cls = next(module.igetattr("MonkeyPatchClass"))
    assert isinstance(cls, nodes.ClassDef)
    assert cls.declared_metaclass() is None


@pytest.mark.xfail(reason="Cannot fully infer all the base classes properly.")
def test_recursion_error_self_reference_type_call() -> None:
    # Fix for https://github.com/pylint-dev/astroid/issues/199
    code = """
    class A(object):
        pass
    class SomeClass(object):
        route_class = A
        def __init__(self):
            self.route_class = type('B', (self.route_class, ), {})
            self.route_class() #@
    """
    node = extract_node(code)
    inferred = next(node.infer())
    assert isinstance(inferred, Instance)
    assert inferred.name == "B"
    # TODO: Cannot infer [B, A, object] but at least the recursion error is gone.
    assert [cls.name for cls in inferred.mro()] == ["B", "A", "object"]


def test_allow_retrieving_instance_attrs_and_special_attrs_for_functions() -> None:
    code = """
    class A:
        def test(self):
            "a"
        # Add `__doc__` to `FunctionDef.instance_attrs` via an `AugAssign`
        test.__doc__ += 'b'
        test #@
    """
    node = extract_node(code)
    inferred = next(node.infer())
    attrs = inferred.getattr("__doc__")
    # One from the `AugAssign`, one from the special attributes
    assert len(attrs) == 2


def test_implicit_parameters_bound_method() -> None:
    code = """
    class A(type):
        @classmethod
        def test(cls, first): return first
        def __new__(cls, name, bases, dictionary):
            return super().__new__(cls, name, bases, dictionary)

    A.test #@
    A.__new__ #@
    """
    test, dunder_new = extract_node(code)
    test = next(test.infer())
    assert isinstance(test, BoundMethod)
    assert test.implicit_parameters() == 1

    dunder_new = next(dunder_new.infer())
    assert isinstance(dunder_new, BoundMethod)
    assert dunder_new.implicit_parameters() == 0


def test_super_inference_of_abstract_property() -> None:
    code = """
    from abc import abstractmethod

    class A:
       @property
       def test(self):
           return "super"

    class C:
       @property
       @abstractmethod
       def test(self):
           "abstract method"

    class B(A, C):

       @property
       def test(self):
            super() #@

    """
    node = extract_node(code)
    inferred = next(node.infer())
    test = inferred.getattr("test")
    assert len(test) == 2


def test_infer_generated_setter() -> None:
    code = """
    class A:
        @property
        def test(self):
            pass
    A.test.setter
    """
    node = extract_node(code)
    inferred = next(node.infer())
    assert isinstance(inferred, nodes.FunctionDef)
    assert isinstance(inferred.args, nodes.Arguments)
    # This line used to crash because property generated functions
    # did not have args properly set
    assert not list(inferred.nodes_of_class(nodes.Const))


def test_infer_list_of_uninferables_does_not_crash() -> None:
    code = """
    x = [A] * 1
    f = [x, [A] * 2]
    x = list(f) + [] # List[Uninferable]
    tuple(x[0])
    """
    node = extract_node(code)
    inferred = next(node.infer())
    assert isinstance(inferred, nodes.Tuple)
    # Would not be able to infer the first element.
    assert not inferred.elts


# https://github.com/pylint-dev/astroid/issues/926
def test_issue926_infer_stmts_referencing_same_name_is_not_uninferable() -> None:
    code = """
    pair = [1, 2]
    ex = pair[0]
    if 1 + 1 == 2:
        ex = pair[1]
    ex
    """
    node = extract_node(code)
    inferred = list(node.infer())
    assert len(inferred) == 2
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == 1
    assert isinstance(inferred[1], nodes.Const)
    assert inferred[1].value == 2


# https://github.com/pylint-dev/astroid/issues/926
def test_issue926_binop_referencing_same_name_is_not_uninferable() -> None:
    code = """
    pair = [1, 2]
    ex = pair[0] + pair[1]
    ex
    """
    node = extract_node(code)
    inferred = list(node.infer())
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == 3


def test_pylint_issue_4692_attribute_inference_error_in_infer_import_from() -> None:
    """Https://github.com/pylint-dev/pylint/issues/4692."""
    code = """
import click


for name, item in click.__dict__.items():
    _ = isinstance(item, click.Command) and item != 'foo'
    """
    node = extract_node(code)
    with pytest.raises(InferenceError):
        list(node.infer())


def test_issue_1090_infer_yield_type_base_class() -> None:
    code = """
import contextlib

class A:
    @contextlib.contextmanager
    def get(self):
        yield self

class B(A):
    def play():
        pass

with B().get() as b:
    b
b
    """
    node = extract_node(code)
    assert next(node.infer()).pytype() == ".B"


def test_namespace_package() -> None:
    """Check that a file using namespace packages and relative imports is parseable."""
    resources.build_file("data/beyond_top_level/import_package.py")


def test_namespace_package_same_name() -> None:
    """Check that a file using namespace packages and relative imports
    with similar names is parseable.
    """
    resources.build_file("data/beyond_top_level_two/a.py")


def test_relative_imports_init_package() -> None:
    """Check that relative imports within a package that uses __init__.py
    still works.
    """
    resources.build_file(
        "data/beyond_top_level_three/module/sub_module/sub_sub_module/main.py"
    )


def test_inference_of_items_on_module_dict() -> None:
    """Crash test for the inference of items() on a module's dict attribute.

    Originally reported in https://github.com/pylint-dev/astroid/issues/1085
    """
    builder.file_build(str(DATA_DIR / "module_dict_items_call" / "test.py"), "models")


def test_imported_module_var_inferable() -> None:
    """
    Module variables can be imported and inferred successfully as part of binary
    operators.
    """
    mod1 = parse(
        textwrap.dedent(
            """
    from top1.mod import v as z
    w = [1] + z
    """
        ),
        module_name="top1",
    )
    parse("v = [2]", module_name="top1.mod")
    w_val = mod1.body[-1].value
    i_w_val = next(w_val.infer())
    assert i_w_val is not util.Uninferable
    assert i_w_val.as_string() == "[1, 2]"


def test_imported_module_var_inferable2() -> None:
    """Version list of strings."""
    mod2 = parse(
        textwrap.dedent(
            """
    from top2.mod import v as z
    w = ['1'] + z
    """
        ),
        module_name="top2",
    )
    parse("v = ['2']", module_name="top2.mod")
    w_val = mod2.body[-1].value
    i_w_val = next(w_val.infer())
    assert i_w_val is not util.Uninferable
    assert i_w_val.as_string() == "['1', '2']"


def test_imported_module_var_inferable3() -> None:
    """Version list of strings with a __dunder__ name."""
    mod3 = parse(
        textwrap.dedent(
            """
    from top3.mod import __dunder_var__ as v
    __dunder_var__ = ['w'] + v
    """
        ),
        module_name="top",
    )
    parse("__dunder_var__ = ['v']", module_name="top3.mod")
    w_val = mod3.body[-1].value
    i_w_val = next(w_val.infer())
    assert i_w_val is not util.Uninferable
    assert i_w_val.as_string() == "['w', 'v']"


@pytest.mark.skipif(
    IS_PYPY, reason="Test run with coverage on PyPy sometimes raises a RecursionError"
)
def test_recursion_on_inference_tip() -> None:
    """Regression test for recursion in inference tip.

    Originally reported in https://github.com/pylint-dev/pylint/issues/5408.

    When run on PyPy with coverage enabled, the test can sometimes raise a RecursionError
    outside of the code that we actually want to test.
    As the issue seems to be with coverage, skip the test on PyPy.
    https://github.com/pylint-dev/astroid/pull/1984#issuecomment-1407720311
    """
    code = """
    class MyInnerClass:
        ...


    class MySubClass:
        inner_class = MyInnerClass


    class MyClass:
        sub_class = MySubClass()


    def get_unpatched_class(cls):
        return cls


    def get_unpatched(item):
        lookup = get_unpatched_class if isinstance(item, type) else lambda item: None
        return lookup(item)


    _Child = get_unpatched(MyClass.sub_class.inner_class)


    class Child(_Child):
        def patch(cls):
            MyClass.sub_class.inner_class = cls
    """
    module = parse(code)
    assert module


def test_function_def_cached_generator() -> None:
    """Regression test for https://github.com/pylint-dev/astroid/issues/817."""
    funcdef: nodes.FunctionDef = extract_node("def func(): pass")
    next(funcdef._infer())


class TestOldStyleStringFormatting:
    @pytest.mark.parametrize(
        "format_string",
        [
            pytest.param(
                """"My name is %s, I'm %s" % ("Daniel", 12)""", id="empty-indexes"
            ),
            pytest.param(
                """"My name is %0s, I'm %1s" % ("Daniel", 12)""",
                id="numbered-indexes",
            ),
            pytest.param(
                """
        fname = "Daniel"
        age = 12
        "My name is %s, I'm %s" % (fname, age)
        """,
                id="empty-indexes-from-positional",
            ),
            pytest.param(
                """
        fname = "Daniel"
        age = 12
        "My name is %0s, I'm %1s" % (fname, age)
        """,
                id="numbered-indexes-from-positionl",
            ),
            pytest.param(
                """
        fname = "Daniel"
        age = 12
        "My name is %(fname)s, I'm %(age)s" % {"fname": fname, "age": age}
        """,
                id="named-indexes-from-keyword",
            ),
            pytest.param(
                """
        string = "My name is %s, I'm %s"
        string % ("Daniel", 12)
        """,
                id="empty-indexes-on-variable",
            ),
            pytest.param(
                """"My name is Daniel, I'm %s" % 12""", id="empty-indexes-from-variable"
            ),
            pytest.param(
                """
                age = 12
                "My name is Daniel, I'm %s" % age
                """,
                id="empty-indexes-from-variable",
            ),
        ],
    )
    def test_old_style_string_formatting(self, format_string: str) -> None:
        node: nodes.Call = _extract_single_node(format_string)
        inferred = next(node.infer())
        assert isinstance(inferred, nodes.Const)
        assert inferred.value == "My name is Daniel, I'm 12"

    @pytest.mark.parametrize(
        "format_string",
        [
            """
            from missing import Unknown
            fname = Unknown
            age = 12
            "My name is %(fname)s, I'm %(age)s" % {"fname": fname, "age": age}
            """,
            """
            from missing import fname
            age = 12
            "My name is %(fname)s, I'm %(age)s" % {"fname": fname, "age": age}
            """,
            """
            from missing import fname
            "My name is %s, I'm %s" % (fname, 12)
            """,
            """
            "My name is %0s, I'm %1s" % ("Daniel")
            """,
            """"I am %s" % ()""",
            """"I am %s" % Exception()""",
            """
            fsname = "Daniel"
            "My name is %(fname)s, I'm %(age)s" % {"fsname": fsname, "age": age}
            """,
            """
            "My name is %(fname)s, I'm %(age)s" % {Exception(): "Daniel", "age": age}
            """,
            """
            fname = "Daniel"
            age = 12
            "My name is %0s, I'm %(age)s" % (fname, age)
            """,
            """
            "My name is %s, I'm %s" % ((fname,)*2)
            """,
            """20 % 0""",
            """("%" + str(20)) % 0""",
        ],
    )
    def test_old_style_string_formatting_uninferable(self, format_string: str) -> None:
        node: nodes.Call = _extract_single_node(format_string)
        inferred = next(node.infer())
        assert inferred is util.Uninferable

    def test_old_style_string_formatting_with_specs(self) -> None:
        node: nodes.Call = _extract_single_node(
            """"My name is %s, I'm %.2f" % ("Daniel", 12)"""
        )
        inferred = next(node.infer())
        assert isinstance(inferred, nodes.Const)
        assert inferred.value == "My name is Daniel, I'm 12.00"


def test_sys_argv_uninferable() -> None:
    """Regression test for https://github.com/pylint-dev/pylint/issues/7710."""
    a: nodes.List = extract_node(
        textwrap.dedent(
            """
    import sys

    sys.argv"""
        )
    )
    sys_argv_value = list(a._infer())
    assert len(sys_argv_value) == 1
    assert sys_argv_value[0] is Uninferable


def test_empty_format_spec() -> None:
    """Regression test for https://github.com/pylint-dev/pylint/issues/9945."""
    node = extract_node('f"{x:}"')
    assert isinstance(node, nodes.JoinedStr)

    assert list(node.infer()) == [util.Uninferable]


@pytest.mark.parametrize(
    "source, expected",
    [
        (
            """
class Cls:
    # pylint: disable=too-few-public-methods
    pass

c_obj = Cls()

s1 = f'{c_obj!r}' #@
""",
            "<__main__.Cls",
        ),
        ("s1 = f'{5}' #@", "5"),
    ],
)
def test_joined_str_returns_string(source, expected) -> None:
    """Regression test for https://github.com/pylint-dev/pylint/issues/9947."""
    node = extract_node(source)
    assert isinstance(node, Assign)
    target = node.targets[0]
    assert target
    inferred = list(target.inferred())
    assert len(inferred) == 1
    assert isinstance(inferred[0], Const)
    inferred[0].value.startswith(expected)
