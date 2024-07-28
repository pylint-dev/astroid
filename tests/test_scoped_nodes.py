# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Tests for specific behaviour of astroid scoped nodes (i.e. module, class and
function).
"""

from __future__ import annotations

import difflib
import os
import sys
import textwrap
import unittest
from functools import partial
from typing import Any
from unittest.mock import patch

import pytest

from astroid import (
    MANAGER,
    builder,
    extract_node,
    nodes,
    objects,
    parse,
    util,
)
from astroid.bases import BoundMethod, Generator, Instance, UnboundMethod
from astroid.const import WIN32
from astroid.exceptions import (
    AstroidBuildingError,
    AttributeInferenceError,
    DuplicateBasesError,
    InconsistentMroError,
    InferenceError,
    MroError,
    NameInferenceError,
    NoDefault,
    ResolveError,
    TooManyLevelsError,
)
from astroid.nodes.scoped_nodes.scoped_nodes import _is_metaclass

from . import resources

try:
    import six  # type: ignore[import]  # pylint: disable=unused-import

    HAS_SIX = True
except ImportError:
    HAS_SIX = False


def _test_dict_interface(
    self: Any,
    node: nodes.ClassDef | nodes.FunctionDef | nodes.Module,
    test_attr: str,
) -> None:
    self.assertIs(node[test_attr], node[test_attr])
    self.assertIn(test_attr, node)
    node.keys()
    node.values()
    node.items()
    iter(node)


class ModuleLoader(resources.SysPathSetup):
    def setUp(self) -> None:
        super().setUp()
        self.module = resources.build_file("data/module.py", "data.module")
        self.module2 = resources.build_file("data/module2.py", "data.module2")
        self.nonregr = resources.build_file("data/nonregr.py", "data.nonregr")
        self.pack = resources.build_file("data/__init__.py", "data")


class ModuleNodeTest(ModuleLoader, unittest.TestCase):
    def test_special_attributes(self) -> None:
        self.assertEqual(len(self.module.getattr("__name__")), 2)
        self.assertIsInstance(self.module.getattr("__name__")[0], nodes.Const)
        self.assertEqual(self.module.getattr("__name__")[0].value, "data.module")
        self.assertIsInstance(self.module.getattr("__name__")[1], nodes.Const)
        self.assertEqual(self.module.getattr("__name__")[1].value, "__main__")
        self.assertEqual(len(self.module.getattr("__doc__")), 1)
        self.assertIsInstance(self.module.getattr("__doc__")[0], nodes.Const)
        self.assertEqual(
            self.module.getattr("__doc__")[0].value, "test module for astroid\n"
        )
        self.assertEqual(len(self.module.getattr("__file__")), 1)
        self.assertIsInstance(self.module.getattr("__file__")[0], nodes.Const)
        self.assertEqual(
            self.module.getattr("__file__")[0].value,
            os.path.abspath(resources.find("data/module.py")),
        )
        self.assertEqual(len(self.module.getattr("__dict__")), 1)
        self.assertIsInstance(self.module.getattr("__dict__")[0], nodes.Dict)
        self.assertRaises(AttributeInferenceError, self.module.getattr, "__path__")
        self.assertEqual(len(self.pack.getattr("__path__")), 1)
        self.assertIsInstance(self.pack.getattr("__path__")[0], nodes.List)

    def test_dict_interface(self) -> None:
        _test_dict_interface(self, self.module, "YO")

    def test_getattr(self) -> None:
        yo = self.module.getattr("YO")[0]
        self.assertIsInstance(yo, nodes.ClassDef)
        self.assertEqual(yo.name, "YO")
        red = next(self.module.igetattr("redirect"))
        self.assertIsInstance(red, nodes.FunctionDef)
        self.assertEqual(red.name, "four_args")
        namenode = next(self.module.igetattr("NameNode"))
        self.assertIsInstance(namenode, nodes.ClassDef)
        self.assertEqual(namenode.name, "Name")
        # resolve packageredirection
        mod = resources.build_file(
            "data/appl/myConnection.py", "data.appl.myConnection"
        )
        ssl = next(mod.igetattr("SSL1"))
        cnx = next(ssl.igetattr("Connection"))
        self.assertEqual(cnx.__class__, nodes.ClassDef)
        self.assertEqual(cnx.name, "Connection")
        self.assertEqual(cnx.root().name, "data.SSL1.Connection1")
        self.assertEqual(len(self.nonregr.getattr("enumerate")), 2)
        self.assertRaises(InferenceError, self.nonregr.igetattr, "YOAA")

    def test_wildcard_import_names(self) -> None:
        m = resources.build_file("data/all.py", "all")
        self.assertEqual(m.wildcard_import_names(), ["Aaa", "_bla", "name"])
        m = resources.build_file("data/notall.py", "notall")
        res = sorted(m.wildcard_import_names())
        self.assertEqual(res, ["Aaa", "func", "name", "other"])

    def test_public_names(self) -> None:
        m = builder.parse(
            """
        name = 'a'
        _bla = 2
        other = 'o'
        class Aaa: pass
        def func(): print('yo')
        __all__ = 'Aaa', '_bla', 'name'
        """
        )
        values = sorted(["Aaa", "name", "other", "func"])
        self.assertEqual(sorted(m.public_names()), values)
        m = builder.parse(
            """
        name = 'a'
        _bla = 2
        other = 'o'
        class Aaa: pass

        def func(): return 'yo'
        """
        )
        res = sorted(m.public_names())
        self.assertEqual(res, values)

        m = builder.parse(
            """
            from missing import tzop
            trop = "test"
            __all__ = (trop, "test1", tzop, 42)
        """
        )
        res = sorted(m.public_names())
        self.assertEqual(res, ["trop", "tzop"])

        m = builder.parse(
            """
            test = tzop = 42
            __all__ = ('test', ) + ('tzop', )
        """
        )
        res = sorted(m.public_names())
        self.assertEqual(res, ["test", "tzop"])

    def test_module_getattr(self) -> None:
        data = """
            appli = application
            appli += 2
            del appli
        """
        astroid = builder.parse(data, __name__)
        # test del statement not returned by getattr
        self.assertEqual(len(astroid.getattr("appli")), 2, astroid.getattr("appli"))

    def test_relative_to_absolute_name(self) -> None:
        # package
        mod = nodes.Module("very.multi.package", package=True)
        modname = mod.relative_to_absolute_name("utils", 1)
        self.assertEqual(modname, "very.multi.package.utils")
        modname = mod.relative_to_absolute_name("utils", 2)
        self.assertEqual(modname, "very.multi.utils")
        modname = mod.relative_to_absolute_name("utils", 0)
        self.assertEqual(modname, "very.multi.package.utils")
        modname = mod.relative_to_absolute_name("", 1)
        self.assertEqual(modname, "very.multi.package")
        # non package
        mod = nodes.Module("very.multi.module", package=False)
        modname = mod.relative_to_absolute_name("utils", 0)
        self.assertEqual(modname, "very.multi.utils")
        modname = mod.relative_to_absolute_name("utils", 1)
        self.assertEqual(modname, "very.multi.utils")
        modname = mod.relative_to_absolute_name("utils", 2)
        self.assertEqual(modname, "very.utils")
        modname = mod.relative_to_absolute_name("", 1)
        self.assertEqual(modname, "very.multi")

    def test_relative_to_absolute_name_beyond_top_level(self) -> None:
        mod = nodes.Module("a.b.c", package=True)
        for level in (5, 4):
            with self.assertRaises(TooManyLevelsError) as cm:
                mod.relative_to_absolute_name("test", level)

            expected = (
                "Relative import with too many levels "
                f"({level-1}) for module {mod.name!r}"
            )
            self.assertEqual(expected, str(cm.exception))

    def test_import_1(self) -> None:
        data = """from . import subpackage"""
        sys.path.insert(0, resources.find("data"))
        astroid = builder.parse(data, "package", "data/package/__init__.py")
        try:
            m = astroid.import_module("", level=1)
            self.assertEqual(m.name, "package")
            inferred = list(astroid.igetattr("subpackage"))
            self.assertEqual(len(inferred), 1)
            self.assertEqual(inferred[0].name, "package.subpackage")
        finally:
            del sys.path[0]

    def test_import_2(self) -> None:
        data = """from . import subpackage as pouet"""
        astroid = builder.parse(data, "package", "data/package/__init__.py")
        sys.path.insert(0, resources.find("data"))
        try:
            m = astroid.import_module("", level=1)
            self.assertEqual(m.name, "package")
            inferred = list(astroid.igetattr("pouet"))
            self.assertEqual(len(inferred), 1)
            self.assertEqual(inferred[0].name, "package.subpackage")
        finally:
            del sys.path[0]

    @patch(
        "astroid.nodes.scoped_nodes.scoped_nodes.AstroidManager.ast_from_module_name"
    )
    def test_import_unavailable_module(self, mock) -> None:
        unavailable_modname = "posixpath" if WIN32 else "ntpath"
        module = builder.parse(f"import {unavailable_modname}")
        mock.side_effect = AstroidBuildingError

        with pytest.raises(AstroidBuildingError):
            module.import_module(unavailable_modname)

        mock.assert_called_once()

    def test_file_stream_in_memory(self) -> None:
        data = """irrelevant_variable is irrelevant"""
        astroid = builder.parse(data, "in_memory")
        with astroid.stream() as stream:
            self.assertEqual(stream.read().decode(), data)

    def test_file_stream_physical(self) -> None:
        path = resources.find("data/all.py")
        astroid = builder.AstroidBuilder().file_build(path, "all")
        with open(path, "rb") as file_io:
            with astroid.stream() as stream:
                self.assertEqual(stream.read(), file_io.read())

    def test_file_stream_api(self) -> None:
        path = resources.find("data/all.py")
        file_build = builder.AstroidBuilder().file_build(path, "all")
        with self.assertRaises(AttributeError):
            # pylint: disable=pointless-statement, no-member
            file_build.file_stream  # noqa: B018

    def test_stream_api(self) -> None:
        path = resources.find("data/all.py")
        astroid = builder.AstroidBuilder().file_build(path, "all")
        stream = astroid.stream()
        self.assertTrue(hasattr(stream, "close"))
        with stream:
            with open(path, "rb") as file_io:
                self.assertEqual(stream.read(), file_io.read())

    @staticmethod
    def test_singleline_docstring() -> None:
        data = textwrap.dedent(
            """\
            '''Hello World'''
            foo = 1
        """
        )
        module = builder.parse(data, __name__)
        assert isinstance(module.doc_node, nodes.Const)
        assert module.doc_node.lineno == 1
        assert module.doc_node.col_offset == 0
        assert module.doc_node.end_lineno == 1
        assert module.doc_node.end_col_offset == 17

    @staticmethod
    def test_multiline_docstring() -> None:
        data = textwrap.dedent(
            """\
            '''Hello World

            Also on this line.
            '''
            foo = 1
        """
        )
        module = builder.parse(data, __name__)

        assert isinstance(module.doc_node, nodes.Const)
        assert module.doc_node.lineno == 1
        assert module.doc_node.col_offset == 0
        assert module.doc_node.end_lineno == 4
        assert module.doc_node.end_col_offset == 3

    @staticmethod
    def test_comment_before_docstring() -> None:
        data = textwrap.dedent(
            """\
            # Some comment
            '''This is

            a multiline docstring.
            '''
        """
        )
        module = builder.parse(data, __name__)

        assert isinstance(module.doc_node, nodes.Const)
        assert module.doc_node.lineno == 2
        assert module.doc_node.col_offset == 0
        assert module.doc_node.end_lineno == 5
        assert module.doc_node.end_col_offset == 3

    @staticmethod
    def test_without_docstring() -> None:
        data = textwrap.dedent(
            """\
            foo = 1
        """
        )
        module = builder.parse(data, __name__)
        assert module.doc_node is None


class FunctionNodeTest(ModuleLoader, unittest.TestCase):
    def test_special_attributes(self) -> None:
        func = self.module2["make_class"]
        self.assertEqual(len(func.getattr("__name__")), 1)
        self.assertIsInstance(func.getattr("__name__")[0], nodes.Const)
        self.assertEqual(func.getattr("__name__")[0].value, "make_class")
        self.assertEqual(len(func.getattr("__doc__")), 1)
        self.assertIsInstance(func.getattr("__doc__")[0], nodes.Const)
        self.assertEqual(
            func.getattr("__doc__")[0].value,
            "check base is correctly resolved to Concrete0",
        )
        self.assertEqual(len(self.module.getattr("__dict__")), 1)
        self.assertIsInstance(self.module.getattr("__dict__")[0], nodes.Dict)

    def test_dict_interface(self) -> None:
        _test_dict_interface(self, self.module["global_access"], "local")

    def test_default_value(self) -> None:
        func = self.module2["make_class"]
        self.assertIsInstance(func.args.default_value("base"), nodes.Attribute)
        self.assertRaises(NoDefault, func.args.default_value, "args")
        self.assertRaises(NoDefault, func.args.default_value, "kwargs")
        self.assertRaises(NoDefault, func.args.default_value, "any")
        # self.assertIsInstance(func.mularg_class('args'), nodes.Tuple)
        # self.assertIsInstance(func.mularg_class('kwargs'), nodes.Dict)
        # self.assertIsNone(func.mularg_class('base'))

    def test_navigation(self) -> None:
        function = self.module["global_access"]
        self.assertEqual(function.statement(), function)
        self.assertEqual(function.statement(), function)
        l_sibling = function.previous_sibling()
        # check taking parent if child is not a stmt
        self.assertIsInstance(l_sibling, nodes.Assign)
        child = function.args.args[0]
        self.assertIs(l_sibling, child.previous_sibling())
        r_sibling = function.next_sibling()
        self.assertIsInstance(r_sibling, nodes.ClassDef)
        self.assertEqual(r_sibling.name, "YO")
        self.assertIs(r_sibling, child.next_sibling())
        last = r_sibling.next_sibling().next_sibling().next_sibling()
        self.assertIsInstance(last, nodes.Assign)
        self.assertIsNone(last.next_sibling())
        first = l_sibling.root().body[0]
        self.assertIsNone(first.previous_sibling())

    def test_four_args(self) -> None:
        func = self.module["four_args"]
        local = sorted(func.keys())
        self.assertEqual(local, ["a", "b", "c", "d"])
        self.assertEqual(func.type, "function")

    def test_format_args(self) -> None:
        func = self.module2["make_class"]
        self.assertEqual(
            func.args.format_args(), "any, base=data.module.YO, *args, **kwargs"
        )
        func = self.module["four_args"]
        self.assertEqual(func.args.format_args(), "a, b, c, d")

    def test_format_args_keyword_only_args(self) -> None:
        node = (
            builder.parse(
                """
        def test(a: int, *, b: dict):
            pass
        """
            )
            .body[-1]
            .args
        )
        formatted = node.format_args()
        self.assertEqual(formatted, "a: int, *, b: dict")

    def test_is_generator(self) -> None:
        self.assertTrue(self.module2["generator"].is_generator())
        self.assertFalse(self.module2["not_a_generator"].is_generator())
        self.assertFalse(self.module2["make_class"].is_generator())

    def test_is_abstract(self) -> None:
        method = self.module2["AbstractClass"]["to_override"]
        self.assertTrue(method.is_abstract(pass_is_abstract=False))
        self.assertEqual(method.qname(), "data.module2.AbstractClass.to_override")
        self.assertEqual(method.pytype(), "builtins.instancemethod")
        method = self.module2["AbstractClass"]["return_something"]
        self.assertFalse(method.is_abstract(pass_is_abstract=False))
        # non regression : test raise "string" doesn't cause an exception in is_abstract
        func = self.module2["raise_string"]
        self.assertFalse(func.is_abstract(pass_is_abstract=False))

    def test_is_abstract_decorated(self) -> None:
        methods = builder.extract_node(
            """
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
         """
        )
        assert len(methods) == 3
        prop, method1, method2 = methods
        assert isinstance(prop, nodes.FunctionDef)
        assert prop.is_abstract(pass_is_abstract=False)

        assert isinstance(method1, nodes.FunctionDef)
        assert method1.is_abstract(pass_is_abstract=False)

        assert isinstance(method2, nodes.FunctionDef)
        assert not method2.is_abstract(pass_is_abstract=False)

    # def test_raises(self):
    #     method = self.module2["AbstractClass"]["to_override"]
    #     self.assertEqual(
    #         [str(term) for term in method.raises()],
    #         ["Call(Name('NotImplementedError'), [], None, None)"],
    #     )

    # def test_returns(self):
    #     method = self.module2["AbstractClass"]["return_something"]
    #     # use string comp since Node doesn't handle __cmp__
    #     self.assertEqual(
    #         [str(term) for term in method.returns()], ["Const('toto')", "Const(None)"]
    #     )

    def test_lambda_pytype(self) -> None:
        data = """
            def f():
                g = lambda: None
        """
        astroid = builder.parse(data)
        g = next(iter(astroid["f"].ilookup("g")))
        self.assertEqual(g.pytype(), "builtins.function")

    def test_lambda_qname(self) -> None:
        astroid = builder.parse("lmbd = lambda: None", __name__)
        self.assertEqual(f"{__name__}.<lambda>", astroid["lmbd"].parent.value.qname())

    def test_lambda_getattr(self) -> None:
        astroid = builder.parse("lmbd = lambda: None")
        self.assertIsInstance(
            astroid["lmbd"].parent.value.getattr("__code__")[0], nodes.Unknown
        )

    def test_is_method(self) -> None:
        data = """
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
        """
        astroid = builder.parse(data)
        self.assertTrue(astroid["A"]["meth1"].is_method())
        self.assertTrue(astroid["A"]["meth2"].is_method())
        self.assertTrue(astroid["A"]["meth3"].is_method())
        self.assertFalse(astroid["function"].is_method())
        self.assertFalse(astroid["sfunction"].is_method())

    def test_argnames(self) -> None:
        code = "def f(a, b, c, *args, **kwargs): pass"
        astroid = builder.parse(code, __name__)
        self.assertEqual(astroid["f"].argnames(), ["a", "b", "c", "args", "kwargs"])

        code_with_kwonly_args = "def f(a, b, *args, c=None, d=None, **kwargs): pass"
        astroid = builder.parse(code_with_kwonly_args, __name__)
        self.assertEqual(
            astroid["f"].argnames(), ["a", "b", "args", "c", "d", "kwargs"]
        )

    def test_argnames_lambda(self) -> None:
        lambda_node = extract_node("lambda a, b, c, *args, **kwargs: ...")
        self.assertEqual(lambda_node.argnames(), ["a", "b", "c", "args", "kwargs"])

    def test_positional_only_argnames(self) -> None:
        code = "def f(a, b, /, c=None, *args, d, **kwargs): pass"
        astroid = builder.parse(code, __name__)
        self.assertEqual(
            astroid["f"].argnames(), ["a", "b", "c", "args", "d", "kwargs"]
        )

    def test_return_nothing(self) -> None:
        """Test inferred value on a function with empty return."""
        data = """
            def func():
                return

            a = func()
        """
        astroid = builder.parse(data)
        call = astroid.body[1].value
        func_vals = call.inferred()
        self.assertEqual(len(func_vals), 1)
        self.assertIsInstance(func_vals[0], nodes.Const)
        self.assertIsNone(func_vals[0].value)

    def test_no_returns_is_implicitly_none(self) -> None:
        code = """
            def f():
                print('non-empty, non-pass, no return statements')
            value = f()
            value
        """
        node = builder.extract_node(code)
        inferred = next(node.infer())
        assert isinstance(inferred, nodes.Const)
        assert inferred.value is None

    def test_only_raises_is_not_implicitly_none(self) -> None:
        code = """
            def f():
                raise SystemExit()
            f()
        """
        node = builder.extract_node(code)
        assert isinstance(node, nodes.Call)
        inferred = next(node.infer())
        assert inferred is util.Uninferable

    def test_abstract_methods_are_not_implicitly_none(self) -> None:
        code = """
            from abc import ABCMeta, abstractmethod

            class Abstract(metaclass=ABCMeta):
                @abstractmethod
                def foo(self):
                    pass
                def bar(self):
                    print('non-empty, non-pass, no return statements')
            Abstract().foo()  #@
            Abstract().bar()  #@

            class Concrete(Abstract):
                def foo(self):
                    return 123
            Concrete().foo()  #@
            Concrete().bar()  #@
        """
        afoo, abar, cfoo, cbar = builder.extract_node(code)

        assert next(afoo.infer()) is util.Uninferable
        for node, value in ((abar, None), (cfoo, 123), (cbar, None)):
            inferred = next(node.infer())
            assert isinstance(inferred, nodes.Const)
            assert inferred.value == value

    def test_func_instance_attr(self) -> None:
        """Test instance attributes for functions."""
        data = """
            def test():
                print(test.bar)

            test.bar = 1
            test()
        """
        astroid = builder.parse(data, "mod")
        func = astroid.body[2].value.func.inferred()[0]
        self.assertIsInstance(func, nodes.FunctionDef)
        self.assertEqual(func.name, "test")
        one = func.getattr("bar")[0].inferred()[0]
        self.assertIsInstance(one, nodes.Const)
        self.assertEqual(one.value, 1)

    def test_func_is_bound(self) -> None:
        data = """
        class MyClass:
            def bound():  #@
                pass
        """
        func = builder.extract_node(data)
        self.assertIs(func.is_bound(), True)
        self.assertEqual(func.implicit_parameters(), 1)

        data2 = """
        def not_bound():  #@
            pass
        """
        func2 = builder.extract_node(data2)
        self.assertIs(func2.is_bound(), False)
        self.assertEqual(func2.implicit_parameters(), 0)

    def test_type_builtin_descriptor_subclasses(self) -> None:
        astroid = builder.parse(
            """
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
        """
        )
        node = astroid.locals["Node"][0]
        self.assertEqual(node.locals["clsmethod_subclass"][0].type, "classmethod")
        self.assertEqual(node.locals["clsmethod"][0].type, "classmethod")
        self.assertEqual(node.locals["staticmethod_subclass"][0].type, "staticmethod")
        self.assertEqual(node.locals["stcmethod"][0].type, "staticmethod")

    def test_decorator_builtin_descriptors(self) -> None:
        astroid = builder.parse(
            """
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
        """
        )
        node = astroid.locals["SomeClass"][0]
        self.assertEqual(node.locals["static"][0].type, "staticmethod")
        self.assertEqual(node.locals["classmethod"][0].type, "classmethod")
        self.assertEqual(node.locals["not_so_static"][0].type, "method")
        self.assertEqual(node.locals["not_so_classmethod"][0].type, "method")
        self.assertEqual(node.locals["classmethod_wrapped"][0].type, "classmethod")
        self.assertEqual(node.locals["staticmethod_wrapped"][0].type, "staticmethod")
        self.assertEqual(node.locals["long_classmethod"][0].type, "classmethod")

    def test_igetattr(self) -> None:
        func = builder.extract_node(
            """
        def test():
            pass
        """
        )
        assert isinstance(func, nodes.FunctionDef)
        func.instance_attrs["value"] = [nodes.Const(42)]
        value = func.getattr("value")
        self.assertEqual(len(value), 1)
        self.assertIsInstance(value[0], nodes.Const)
        self.assertEqual(value[0].value, 42)
        inferred = next(func.igetattr("value"))
        self.assertIsInstance(inferred, nodes.Const)
        self.assertEqual(inferred.value, 42)

    def test_return_annotation_is_not_the_last(self) -> None:
        func = builder.extract_node(
            """
        def test() -> bytes:
            pass
            pass
            return
        """
        )
        last_child = func.last_child()
        self.assertIsInstance(last_child, nodes.Return)
        self.assertEqual(func.tolineno, 5)

    def test_method_init_subclass(self) -> None:
        klass = builder.extract_node(
            """
        class MyClass:
            def __init_subclass__(cls):
                pass
        """
        )
        method = klass["__init_subclass__"]
        self.assertEqual([n.name for n in method.args.args], ["cls"])
        self.assertEqual(method.type, "classmethod")

    def test_dunder_class_local_to_method(self) -> None:
        node = builder.extract_node(
            """
        class MyClass:
            def test(self):
                __class__ #@
        """
        )
        inferred = next(node.infer())
        self.assertIsInstance(inferred, nodes.ClassDef)
        self.assertEqual(inferred.name, "MyClass")

    def test_dunder_class_local_to_function(self) -> None:
        node = builder.extract_node(
            """
        def test(self):
            __class__ #@
        """
        )
        with self.assertRaises(NameInferenceError):
            next(node.infer())

    def test_dunder_class_local_to_classmethod(self) -> None:
        node = builder.extract_node(
            """
        class MyClass:
            @classmethod
            def test(cls):
                __class__ #@
        """
        )
        inferred = next(node.infer())
        self.assertIsInstance(inferred, nodes.ClassDef)
        self.assertEqual(inferred.name, "MyClass")

    @staticmethod
    def test_singleline_docstring() -> None:
        code = textwrap.dedent(
            """\
            def foo():
                '''Hello World'''
                bar = 1
        """
        )
        func: nodes.FunctionDef = builder.extract_node(code)  # type: ignore[assignment]

        assert isinstance(func.doc_node, nodes.Const)
        assert func.doc_node.lineno == 2
        assert func.doc_node.col_offset == 4
        assert func.doc_node.end_lineno == 2
        assert func.doc_node.end_col_offset == 21

    @staticmethod
    def test_multiline_docstring() -> None:
        code = textwrap.dedent(
            """\
            def foo():
                '''Hello World

                Also on this line.
                '''
                bar = 1
        """
        )
        func: nodes.FunctionDef = builder.extract_node(code)  # type: ignore[assignment]

        assert isinstance(func.doc_node, nodes.Const)
        assert func.doc_node.lineno == 2
        assert func.doc_node.col_offset == 4
        assert func.doc_node.end_lineno == 5
        assert func.doc_node.end_col_offset == 7

    @staticmethod
    def test_multiline_docstring_async() -> None:
        code = textwrap.dedent(
            """\
            async def foo(var: tuple = ()):
                '''Hello

                World
                '''
        """
        )
        func: nodes.FunctionDef = builder.extract_node(code)  # type: ignore[assignment]

        assert isinstance(func.doc_node, nodes.Const)
        assert func.doc_node.lineno == 2
        assert func.doc_node.col_offset == 4
        assert func.doc_node.end_lineno == 5
        assert func.doc_node.end_col_offset == 7

    @staticmethod
    def test_docstring_special_cases() -> None:
        code = textwrap.dedent(
            """\
        def f1(var: tuple = ()):  #@
            'Hello World'

        def f2() -> "just some comment with an open bracket(":  #@
            'Hello World'

        def f3() -> "Another comment with a colon: ":  #@
            'Hello World'

        def f4():  #@
            # It should work with comments too
            'Hello World'
        """
        )
        ast_nodes: list[nodes.FunctionDef] = builder.extract_node(code)  # type: ignore[assignment]
        assert len(ast_nodes) == 4

        assert isinstance(ast_nodes[0].doc_node, nodes.Const)
        assert ast_nodes[0].doc_node.lineno == 2
        assert ast_nodes[0].doc_node.col_offset == 4
        assert ast_nodes[0].doc_node.end_lineno == 2
        assert ast_nodes[0].doc_node.end_col_offset == 17

        assert isinstance(ast_nodes[1].doc_node, nodes.Const)
        assert ast_nodes[1].doc_node.lineno == 5
        assert ast_nodes[1].doc_node.col_offset == 4
        assert ast_nodes[1].doc_node.end_lineno == 5
        assert ast_nodes[1].doc_node.end_col_offset == 17

        assert isinstance(ast_nodes[2].doc_node, nodes.Const)
        assert ast_nodes[2].doc_node.lineno == 8
        assert ast_nodes[2].doc_node.col_offset == 4
        assert ast_nodes[2].doc_node.end_lineno == 8
        assert ast_nodes[2].doc_node.end_col_offset == 17

        assert isinstance(ast_nodes[3].doc_node, nodes.Const)
        assert ast_nodes[3].doc_node.lineno == 12
        assert ast_nodes[3].doc_node.col_offset == 4
        assert ast_nodes[3].doc_node.end_lineno == 12
        assert ast_nodes[3].doc_node.end_col_offset == 17

    @staticmethod
    def test_without_docstring() -> None:
        code = textwrap.dedent(
            """\
            def foo():
                bar = 1
        """
        )
        func: nodes.FunctionDef = builder.extract_node(code)  # type: ignore[assignment]
        assert func.doc_node is None

    @staticmethod
    def test_display_type() -> None:
        code = textwrap.dedent(
            """\
            def foo():
                bar = 1
        """
        )
        func: nodes.FunctionDef = builder.extract_node(code)  # type: ignore[assignment]
        assert func.display_type() == "Function"

        code = textwrap.dedent(
            """\
            class A:
                def foo(self):  #@
                    bar = 1
        """
        )
        func: nodes.FunctionDef = builder.extract_node(code)  # type: ignore[assignment]
        assert func.display_type() == "Method"

    @staticmethod
    def test_inference_error() -> None:
        code = textwrap.dedent(
            """\
            def foo():
                bar = 1
        """
        )
        func: nodes.FunctionDef = builder.extract_node(code)  # type: ignore[assignment]
        with pytest.raises(AttributeInferenceError):
            func.getattr("")


class ClassNodeTest(ModuleLoader, unittest.TestCase):
    def test_dict_interface(self) -> None:
        _test_dict_interface(self, self.module["YOUPI"], "method")

    def test_cls_special_attributes_1(self) -> None:
        cls = self.module["YO"]
        self.assertEqual(len(cls.getattr("__bases__")), 1)
        self.assertEqual(len(cls.getattr("__name__")), 1)
        self.assertIsInstance(cls.getattr("__name__")[0], nodes.Const)
        self.assertEqual(cls.getattr("__name__")[0].value, "YO")
        self.assertEqual(len(cls.getattr("__doc__")), 1)
        self.assertIsInstance(cls.getattr("__doc__")[0], nodes.Const)
        self.assertEqual(cls.getattr("__doc__")[0].value, "hehe\n    haha")
        # YO is an old styled class for Python 2.7
        # May want to stop locals from referencing namespaced variables in the future
        module_attr_num = 4
        self.assertEqual(len(cls.getattr("__module__")), module_attr_num)
        self.assertIsInstance(cls.getattr("__module__")[0], nodes.Const)
        self.assertEqual(cls.getattr("__module__")[0].value, "data.module")
        self.assertEqual(len(cls.getattr("__dict__")), 1)
        if not cls.newstyle:
            self.assertRaises(AttributeInferenceError, cls.getattr, "__mro__")
        for cls in (nodes.List._proxied, nodes.Const(1)._proxied):
            self.assertEqual(len(cls.getattr("__bases__")), 1)
            self.assertEqual(len(cls.getattr("__name__")), 1)
            self.assertEqual(
                len(cls.getattr("__doc__")), 1, (cls, cls.getattr("__doc__"))
            )
            self.assertEqual(cls.getattr("__doc__")[0].value, cls.doc_node.value)
            self.assertEqual(len(cls.getattr("__module__")), 4)
            self.assertEqual(len(cls.getattr("__dict__")), 1)
            self.assertEqual(len(cls.getattr("__mro__")), 1)

    def test__mro__attribute(self) -> None:
        node = builder.extract_node(
            """
        class A(object): pass
        class B(object): pass
        class C(A, B): pass
        """
        )
        assert isinstance(node, nodes.ClassDef)
        mro = node.getattr("__mro__")[0]
        self.assertIsInstance(mro, nodes.Tuple)
        self.assertEqual(mro.elts, node.mro())

    def test__bases__attribute(self) -> None:
        node = builder.extract_node(
            """
        class A(object): pass
        class B(object): pass
        class C(A, B): pass
        class D(C): pass
        """
        )
        assert isinstance(node, nodes.ClassDef)
        bases = node.getattr("__bases__")[0]
        self.assertIsInstance(bases, nodes.Tuple)
        self.assertEqual(len(bases.elts), 1)
        self.assertIsInstance(bases.elts[0], nodes.ClassDef)
        self.assertEqual(bases.elts[0].name, "C")

    def test_cls_special_attributes_2(self) -> None:
        astroid = builder.parse(
            """
            class A(object): pass
            class B(object): pass

            A.__bases__ += (B,)
        """,
            __name__,
        )
        self.assertEqual(len(astroid["A"].getattr("__bases__")), 2)
        self.assertIsInstance(astroid["A"].getattr("__bases__")[1], nodes.Tuple)
        self.assertIsInstance(astroid["A"].getattr("__bases__")[0], nodes.AssignAttr)

    def test_instance_special_attributes(self) -> None:
        for inst in (Instance(self.module["YO"]), nodes.List(), nodes.Const(1)):
            self.assertRaises(AttributeInferenceError, inst.getattr, "__mro__")
            self.assertRaises(AttributeInferenceError, inst.getattr, "__bases__")
            self.assertRaises(AttributeInferenceError, inst.getattr, "__name__")
            self.assertEqual(len(inst.getattr("__dict__")), 1)
            self.assertEqual(len(inst.getattr("__doc__")), 1)

    def test_navigation(self) -> None:
        klass = self.module["YO"]
        self.assertEqual(klass.statement(), klass)
        self.assertEqual(klass.statement(), klass)
        l_sibling = klass.previous_sibling()
        self.assertTrue(isinstance(l_sibling, nodes.FunctionDef), l_sibling)
        self.assertEqual(l_sibling.name, "global_access")
        r_sibling = klass.next_sibling()
        self.assertIsInstance(r_sibling, nodes.ClassDef)
        self.assertEqual(r_sibling.name, "YOUPI")

    def test_local_attr_ancestors(self) -> None:
        module = builder.parse(
            """
        class A():
            def __init__(self): pass
        class B(A): pass
        class C(B): pass
        class D(object): pass
        class F(): pass
        class E(F, D): pass
        """
        )
        # Test old-style (Python 2) / new-style (Python 3+) ancestors lookups
        klass2 = module["C"]
        it = klass2.local_attr_ancestors("__init__")
        anc_klass = next(it)
        self.assertIsInstance(anc_klass, nodes.ClassDef)
        self.assertEqual(anc_klass.name, "A")
        anc_klass = next(it)
        self.assertIsInstance(anc_klass, nodes.ClassDef)
        self.assertEqual(anc_klass.name, "object")
        self.assertRaises(StopIteration, partial(next, it))

        it = klass2.local_attr_ancestors("method")
        self.assertRaises(StopIteration, partial(next, it))

        # Test mixed-style ancestor lookups
        klass2 = module["E"]
        it = klass2.local_attr_ancestors("__init__")
        anc_klass = next(it)
        self.assertIsInstance(anc_klass, nodes.ClassDef)
        self.assertEqual(anc_klass.name, "object")
        self.assertRaises(StopIteration, partial(next, it))

    def test_local_attr_mro(self) -> None:
        module = builder.parse(
            """
        class A(object):
            def __init__(self): pass
        class B(A):
            def __init__(self, arg, arg2): pass
        class C(A): pass
        class D(C, B): pass
        """
        )
        dclass = module["D"]
        init = dclass.local_attr("__init__")[0]
        self.assertIsInstance(init, nodes.FunctionDef)
        self.assertEqual(init.parent.name, "B")

        cclass = module["C"]
        init = cclass.local_attr("__init__")[0]
        self.assertIsInstance(init, nodes.FunctionDef)
        self.assertEqual(init.parent.name, "A")

        ancestors = list(dclass.local_attr_ancestors("__init__"))
        self.assertEqual([node.name for node in ancestors], ["B", "A", "object"])

    def test_instance_attr_ancestors(self) -> None:
        klass2 = self.module["YOUPI"]
        it = klass2.instance_attr_ancestors("yo")
        anc_klass = next(it)
        self.assertIsInstance(anc_klass, nodes.ClassDef)
        self.assertEqual(anc_klass.name, "YO")
        self.assertRaises(StopIteration, partial(next, it))
        klass2 = self.module["YOUPI"]
        it = klass2.instance_attr_ancestors("member")
        self.assertRaises(StopIteration, partial(next, it))

    def test_methods(self) -> None:
        expected_methods = {"__init__", "class_method", "method", "static_method"}
        klass2 = self.module["YOUPI"]
        methods = {m.name for m in klass2.methods()}
        self.assertTrue(methods.issuperset(expected_methods))
        methods = {m.name for m in klass2.mymethods()}
        self.assertSetEqual(expected_methods, methods)
        klass2 = self.module2["Specialization"]
        methods = {m.name for m in klass2.mymethods()}
        self.assertSetEqual(set(), methods)
        method_locals = klass2.local_attr("method")
        self.assertEqual(len(method_locals), 1)
        self.assertEqual(method_locals[0].name, "method")
        self.assertRaises(AttributeInferenceError, klass2.local_attr, "nonexistent")
        methods = {m.name for m in klass2.methods()}
        self.assertTrue(methods.issuperset(expected_methods))

    # def test_rhs(self):
    #    my_dict = self.module['MY_DICT']
    #    self.assertIsInstance(my_dict.rhs(), nodes.Dict)
    #    a = self.module['YO']['a']
    #    value = a.rhs()
    #    self.assertIsInstance(value, nodes.Const)
    #    self.assertEqual(value.value, 1)

    def test_ancestors(self) -> None:
        klass = self.module["YOUPI"]
        self.assertEqual(["YO", "object"], [a.name for a in klass.ancestors()])
        klass = self.module2["Specialization"]
        self.assertEqual(["YOUPI", "YO", "object"], [a.name for a in klass.ancestors()])

    def test_type(self) -> None:
        klass = self.module["YOUPI"]
        self.assertEqual(klass.type, "class")
        klass = self.module2["Metaclass"]
        self.assertEqual(klass.type, "metaclass")
        klass = self.module2["MyException"]
        self.assertEqual(klass.type, "exception")
        klass = self.module2["MyError"]
        self.assertEqual(klass.type, "exception")
        # the following class used to be detected as a metaclass
        # after the fix which used instance._proxied in .ancestors(),
        # when in fact it is a normal class
        klass = self.module2["NotMetaclass"]
        self.assertEqual(klass.type, "class")

    def test_inner_classes(self) -> None:
        eee = self.nonregr["Ccc"]["Eee"]
        self.assertEqual([n.name for n in eee.ancestors()], ["Ddd", "Aaa", "object"])

    def test_classmethod_attributes(self) -> None:
        data = """
            class WebAppObject(object):
                def registered(cls, application):
                    cls.appli = application
                    cls.schema = application.schema
                    cls.config = application.config
                    return cls
                registered = classmethod(registered)
        """
        astroid = builder.parse(data, __name__)
        cls = astroid["WebAppObject"]
        assert_keys = [
            "__annotations__",
            "__module__",
            "__qualname__",
            "appli",
            "config",
            "registered",
            "schema",
        ]
        self.assertEqual(sorted(cls.locals.keys()), assert_keys)

    def test_class_getattr(self) -> None:
        data = """
            class WebAppObject(object):
                appli = application
                appli += 2
                del self.appli
        """
        astroid = builder.parse(data, __name__)
        cls = astroid["WebAppObject"]
        # test del statement not returned by getattr
        self.assertEqual(len(cls.getattr("appli")), 2)

    def test_instance_getattr(self) -> None:
        data = """
            class WebAppObject(object):
                def __init__(self, application):
                    self.appli = application
                    self.appli += 2
                    del self.appli
         """
        astroid = builder.parse(data)
        inst = Instance(astroid["WebAppObject"])
        # test del statement not returned by getattr
        self.assertEqual(len(inst.getattr("appli")), 2)

    def test_instance_getattr_with_class_attr(self) -> None:
        data = """
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
        """
        astroid = builder.parse(data)
        inst = Instance(astroid["Klass"])
        self.assertEqual(len(inst.getattr("aa")), 3, inst.getattr("aa"))
        self.assertEqual(len(inst.getattr("bb")), 1, inst.getattr("bb"))
        self.assertEqual(len(inst.getattr("cc")), 2, inst.getattr("cc"))

    def test_getattr_method_transform(self) -> None:
        data = """
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
        """
        astroid = builder.parse(data)
        cls = astroid["Clazz"]
        # test del statement not returned by getattr
        for method in ("m1", "m2", "m3"):
            inferred = list(cls.igetattr(method))
            self.assertEqual(len(inferred), 1)
            self.assertIsInstance(inferred[0], UnboundMethod)
            inferred = list(Instance(cls).igetattr(method))
            self.assertEqual(len(inferred), 1)
            self.assertIsInstance(inferred[0], BoundMethod)
        inferred = list(Instance(cls).igetattr("m4"))
        self.assertEqual(len(inferred), 1)
        self.assertIsInstance(inferred[0], nodes.FunctionDef)

    def test_getattr_from_grandpa(self) -> None:
        data = """
            class Future:
                attr = 1

            class Present(Future):
                pass

            class Past(Present):
                pass
        """
        astroid = builder.parse(data)
        past = astroid["Past"]
        attr = past.getattr("attr")
        self.assertEqual(len(attr), 1)
        attr1 = attr[0]
        self.assertIsInstance(attr1, nodes.AssignName)
        self.assertEqual(attr1.name, "attr")

    @staticmethod
    def test_getattr_with_enpty_annassign() -> None:
        code = """
            class Parent:
                attr: int = 2

            class Child(Parent):  #@
                attr: int
        """
        child = extract_node(code)
        attr = child.getattr("attr")
        assert len(attr) == 1
        assert isinstance(attr[0], nodes.AssignName)
        assert attr[0].name == "attr"
        assert attr[0].lineno == 3

    def test_function_with_decorator_lineno(self) -> None:
        data = """
            @f(a=2,
               b=3)
            def g1(x):
                print(x)

            @f(a=2,
               b=3,
            )
            def g2():
                pass
        """
        astroid = builder.parse(data)
        self.assertEqual(astroid["g1"].fromlineno, 4)
        self.assertEqual(astroid["g1"].tolineno, 5)
        self.assertEqual(astroid["g2"].fromlineno, 10)
        self.assertEqual(astroid["g2"].tolineno, 11)

    def test_metaclass_error(self) -> None:
        astroid = builder.parse(
            """
            class Test(object):
                __metaclass__ = typ
        """
        )
        klass = astroid["Test"]
        self.assertFalse(klass.metaclass())

    def test_metaclass_yes_leak(self) -> None:
        astroid = builder.parse(
            """
            # notice `ab` instead of `abc`
            from ab import ABCMeta

            class Meta(object):
                __metaclass__ = ABCMeta
        """
        )
        klass = astroid["Meta"]
        self.assertIsNone(klass.metaclass())

    def test_metaclass_type(self) -> None:
        klass = builder.extract_node(
            """
            def with_metaclass(meta, base=object):
                return meta("NewBase", (base, ), {})

            class ClassWithMeta(with_metaclass(type)): #@
                pass
        """
        )
        assert isinstance(klass, nodes.ClassDef)
        self.assertEqual(
            ["NewBase", "object"], [base.name for base in klass.ancestors()]
        )

    def test_no_infinite_metaclass_loop(self) -> None:
        klass = builder.extract_node(
            """
            class SSS(object):

                class JJJ(object):
                    pass

                @classmethod
                def Init(cls):
                    cls.JJJ = type('JJJ', (cls.JJJ,), {})

            class AAA(SSS):
                pass

            class BBB(AAA.JJJ):
                pass
        """
        )
        assert isinstance(klass, nodes.ClassDef)
        self.assertFalse(_is_metaclass(klass))
        ancestors = [base.name for base in klass.ancestors()]
        self.assertIn("object", ancestors)
        self.assertIn("JJJ", ancestors)

    def test_no_infinite_metaclass_loop_with_redefine(self) -> None:
        ast_nodes = builder.extract_node(
            """
            import datetime

            class A(datetime.date): #@
                @classmethod
                def now(cls):
                    return cls()

            class B(datetime.date): #@
                pass

            datetime.date = A
            datetime.date = B
        """
        )
        for klass in ast_nodes:
            self.assertEqual(None, klass.metaclass())

    @unittest.skipUnless(HAS_SIX, "These tests require the six library")
    def test_metaclass_generator_hack(self):
        klass = builder.extract_node(
            """
            import six

            class WithMeta(six.with_metaclass(type, object)): #@
                pass
        """
        )
        assert isinstance(klass, nodes.ClassDef)
        self.assertEqual(["object"], [base.name for base in klass.ancestors()])
        self.assertEqual("type", klass.metaclass().name)

    @unittest.skipUnless(HAS_SIX, "These tests require the six library")
    def test_metaclass_generator_hack_enum_base(self):
        """Regression test for https://github.com/pylint-dev/pylint/issues/5935"""
        klass = builder.extract_node(
            """
            import six
            from enum import Enum, EnumMeta

            class PetEnumPy2Metaclass(six.with_metaclass(EnumMeta, Enum)): #@
                DOG = "dog"
        """
        )
        self.assertEqual(list(klass.local_attr_ancestors("DOG")), [])

    def test_add_metaclass(self) -> None:
        klass = builder.extract_node(
            """
        import abc

        class WithMeta(object, metaclass=abc.ABCMeta):
            pass
        """
        )
        assert isinstance(klass, nodes.ClassDef)
        inferred = next(klass.infer())
        metaclass = inferred.metaclass()
        self.assertIsInstance(metaclass, nodes.ClassDef)
        self.assertIn(metaclass.qname(), ("abc.ABCMeta", "_py_abc.ABCMeta"))

    @unittest.skipUnless(HAS_SIX, "These tests require the six library")
    def test_using_invalid_six_add_metaclass_call(self):
        klass = builder.extract_node(
            """
        import six
        @six.add_metaclass()
        class Invalid(object):
            pass
        """
        )
        inferred = next(klass.infer())
        self.assertIsNone(inferred.metaclass())

    @staticmethod
    def test_with_invalid_metaclass():
        klass = extract_node(
            """
        class InvalidAsMetaclass: ...

        class Invalid(metaclass=InvalidAsMetaclass()):  #@
            pass
        """
        )
        inferred = next(klass.infer())
        metaclass = inferred.metaclass()
        assert isinstance(metaclass, Instance)

    def test_nonregr_infer_callresult(self) -> None:
        astroid = builder.parse(
            """
            class Delegate(object):
                def __get__(self, obj, cls):
                    return getattr(obj._subject, self.attribute)

            class CompositeBuilder(object):
                __call__ = Delegate()

            builder = CompositeBuilder(result, composite)
            tgts = builder()
        """
        )
        instance = astroid["tgts"]
        # used to raise "'_Yes' object is not iterable", see
        # https://bitbucket.org/logilab/astroid/issue/17
        self.assertEqual(list(instance.infer()), [util.Uninferable])

    def test_slots(self) -> None:
        astroid = builder.parse(
            """
            from collections import deque
            from textwrap import dedent

            class First(object): #@
                __slots__ = ("a", "b", 1)
            class Second(object): #@
                __slots__ = "a"
            class Third(object): #@
                __slots__ = deque(["a", "b", "c"])
            class Fourth(object): #@
                __slots__ = {"a": "a", "b": "b"}
            class Fifth(object): #@
                __slots__ = list
            class Sixth(object): #@
                __slots__ = ""
            class Seventh(object): #@
                __slots__ = dedent.__name__
            class Eight(object): #@
                __slots__ = ("parens")
            class Ninth(object): #@
                pass
            class Ten(object): #@
                __slots__ = dict({"a": "b", "c": "d"})
        """
        )
        expected = [
            ("First", ("a", "b")),
            ("Second", ("a",)),
            ("Third", None),
            ("Fourth", ("a", "b")),
            ("Fifth", None),
            ("Sixth", None),
            ("Seventh", ("dedent",)),
            ("Eight", ("parens",)),
            ("Ninth", None),
            ("Ten", ("a", "c")),
        ]
        for cls, expected_value in expected:
            slots = astroid[cls].slots()
            if expected_value is None:
                self.assertIsNone(slots)
            else:
                self.assertEqual(list(expected_value), [node.value for node in slots])

    def test_slots_for_dict_keys(self) -> None:
        module = builder.parse(
            """
        class Issue(object):
          SlotDefaults = {'id': 0, 'id1':1}
          __slots__ = SlotDefaults.keys()
        """
        )
        cls = module["Issue"]
        slots = cls.slots()
        self.assertEqual(len(slots), 2)
        self.assertEqual(slots[0].value, "id")
        self.assertEqual(slots[1].value, "id1")

    def test_slots_empty_list_of_slots(self) -> None:
        module = builder.parse(
            """
        class Klass(object):
            __slots__ = ()
        """
        )
        cls = module["Klass"]
        self.assertEqual(cls.slots(), [])

    def test_slots_taken_from_parents(self) -> None:
        module = builder.parse(
            """
        class FirstParent(object):
            __slots__ = ('a', 'b', 'c')
        class SecondParent(FirstParent):
            __slots__ = ('d', 'e')
        class Third(SecondParent):
            __slots__ = ('d', )
        """
        )
        cls = module["Third"]
        slots = cls.slots()
        self.assertEqual(
            sorted({slot.value for slot in slots}), ["a", "b", "c", "d", "e"]
        )

    def test_all_ancestors_need_slots(self) -> None:
        module = builder.parse(
            """
        class A(object):
            __slots__ = ('a', )
        class B(A): pass
        class C(B):
            __slots__ = ('a', )
        """
        )
        cls = module["C"]
        self.assertIsNone(cls.slots())
        cls = module["B"]
        self.assertIsNone(cls.slots())

    def test_slots_added_dynamically_still_inferred(self) -> None:
        code = """
        class NodeBase(object):
            __slots__ = "a", "b"

            if Options.isFullCompat():
                __slots__ += ("c",)

        """
        node = builder.extract_node(code)
        inferred = next(node.infer())
        slots = inferred.slots()
        assert len(slots) == 3, slots
        assert [slot.value for slot in slots] == ["a", "b", "c"]

    def assertEqualMro(self, klass: nodes.ClassDef, expected_mro: list[str]) -> None:
        self.assertEqual([member.name for member in klass.mro()], expected_mro)

    def assertEqualMroQName(
        self, klass: nodes.ClassDef, expected_mro: list[str]
    ) -> None:
        self.assertEqual([member.qname() for member in klass.mro()], expected_mro)

    @unittest.skipUnless(HAS_SIX, "These tests require the six library")
    def test_with_metaclass_mro(self):
        astroid = builder.parse(
            """
        import six

        class C(object):
            pass
        class B(C):
            pass
        class A(six.with_metaclass(type, B)):
            pass
        """
        )
        self.assertEqualMro(astroid["A"], ["A", "B", "C", "object"])

    def test_mro(self) -> None:
        astroid = builder.parse(
            """
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
        class Duplicates(str, str): pass

        """
        )
        self.assertEqualMro(astroid["D"], ["D", "dict", "C", "object"])
        self.assertEqualMro(astroid["D1"], ["D1", "B1", "C1", "A1", "object"])
        self.assertEqualMro(astroid["E1"], ["E1", "C1", "B1", "A1", "object"])
        with self.assertRaises(InconsistentMroError) as cm:
            astroid["F1"].mro()
        A1 = astroid.getattr("A1")[0]
        B1 = astroid.getattr("B1")[0]
        C1 = astroid.getattr("C1")[0]
        object_ = MANAGER.astroid_cache["builtins"].getattr("object")[0]
        self.assertEqual(
            cm.exception.mros, [[B1, C1, A1, object_], [C1, B1, A1, object_]]
        )
        with self.assertRaises(InconsistentMroError) as cm:
            astroid["G1"].mro()
        self.assertEqual(
            cm.exception.mros, [[C1, B1, A1, object_], [B1, C1, A1, object_]]
        )
        self.assertEqualMro(
            astroid["PedalWheelBoat"],
            ["PedalWheelBoat", "EngineLess", "DayBoat", "WheelBoat", "Boat", "object"],
        )

        self.assertEqualMro(
            astroid["SmallCatamaran"],
            ["SmallCatamaran", "SmallMultihull", "DayBoat", "Boat", "object"],
        )

        self.assertEqualMro(
            astroid["Pedalo"],
            [
                "Pedalo",
                "PedalWheelBoat",
                "EngineLess",
                "SmallCatamaran",
                "SmallMultihull",
                "DayBoat",
                "WheelBoat",
                "Boat",
                "object",
            ],
        )

        self.assertEqualMro(
            astroid["OuterD"]["Inner"], ["Inner", "Inner", "Inner", "Inner", "object"]
        )

        with self.assertRaises(DuplicateBasesError) as cm:
            astroid["Duplicates"].mro()
        Duplicates = astroid.getattr("Duplicates")[0]
        self.assertEqual(cm.exception.cls, Duplicates)
        self.assertIsInstance(cm.exception, MroError)
        self.assertIsInstance(cm.exception, ResolveError)

    def test_mro_with_factories(self) -> None:
        cls = builder.extract_node(
            """
        def MixinFactory(cls):
            mixin_name = '{}Mixin'.format(cls.__name__)
            mixin_bases = (object,)
            mixin_attrs = {}
            mixin = type(mixin_name, mixin_bases, mixin_attrs)
            return mixin
        class MixinA(MixinFactory(int)):
            pass
        class MixinB(MixinFactory(str)):
            pass
        class Base(object):
            pass
        class ClassA(MixinA, Base):
            pass
        class ClassB(MixinB, ClassA):
            pass
        class FinalClass(ClassB):
            def __init__(self):
                self.name = 'x'
        """
        )
        assert isinstance(cls, nodes.ClassDef)
        self.assertEqualMro(
            cls,
            [
                "FinalClass",
                "ClassB",
                "MixinB",
                "strMixin",
                "ClassA",
                "MixinA",
                "intMixin",
                "Base",
                "object",
            ],
        )

    def test_mro_with_attribute_classes(self) -> None:
        cls = builder.extract_node(
            """
        class A:
            pass
        class B:
            pass
        class Scope:
            pass
        scope = Scope()
        scope.A = A
        scope.B = B
        class C(scope.A, scope.B):
            pass
        """
        )
        assert isinstance(cls, nodes.ClassDef)
        self.assertEqualMro(cls, ["C", "A", "B", "object"])

    def test_mro_generic_1(self):
        cls = builder.extract_node(
            """
        import typing
        T = typing.TypeVar('T')
        class A(typing.Generic[T]): ...
        class B: ...
        class C(A[T], B): ...
        """
        )
        assert isinstance(cls, nodes.ClassDef)
        self.assertEqualMroQName(
            cls, [".C", ".A", "typing.Generic", ".B", "builtins.object"]
        )

    def test_mro_generic_2(self):
        cls = builder.extract_node(
            """
        from typing import Generic, TypeVar
        T = TypeVar('T')
        class A: ...
        class B(Generic[T]): ...
        class C(Generic[T], A, B[T]): ...
        """
        )
        assert isinstance(cls, nodes.ClassDef)
        self.assertEqualMroQName(
            cls, [".C", ".A", ".B", "typing.Generic", "builtins.object"]
        )

    def test_mro_generic_3(self):
        cls = builder.extract_node(
            """
        from typing import Generic, TypeVar
        T = TypeVar('T')
        class A: ...
        class B(A, Generic[T]): ...
        class C(Generic[T]): ...
        class D(B[T], C[T], Generic[T]): ...
        """
        )
        assert isinstance(cls, nodes.ClassDef)
        self.assertEqualMroQName(
            cls, [".D", ".B", ".A", ".C", "typing.Generic", "builtins.object"]
        )

    def test_mro_generic_4(self):
        cls = builder.extract_node(
            """
        from typing import Generic, TypeVar
        T = TypeVar('T')
        class A: ...
        class B(Generic[T]): ...
        class C(A, Generic[T], B[T]): ...
        """
        )
        assert isinstance(cls, nodes.ClassDef)
        self.assertEqualMroQName(
            cls, [".C", ".A", ".B", "typing.Generic", "builtins.object"]
        )

    def test_mro_generic_5(self):
        cls = builder.extract_node(
            """
        from typing import Generic, TypeVar
        T1 = TypeVar('T1')
        T2 = TypeVar('T2')
        class A(Generic[T1]): ...
        class B(Generic[T2]): ...
        class C(A[T1], B[T2]): ...
        """
        )
        assert isinstance(cls, nodes.ClassDef)
        self.assertEqualMroQName(
            cls, [".C", ".A", ".B", "typing.Generic", "builtins.object"]
        )

    def test_mro_generic_6(self):
        cls = builder.extract_node(
            """
        from typing import Generic as TGeneric, TypeVar
        T = TypeVar('T')
        class Generic: ...
        class A(Generic): ...
        class B(TGeneric[T]): ...
        class C(A, B[T]): ...
        """
        )
        assert isinstance(cls, nodes.ClassDef)
        self.assertEqualMroQName(
            cls, [".C", ".A", ".Generic", ".B", "typing.Generic", "builtins.object"]
        )

    def test_mro_generic_7(self):
        cls = builder.extract_node(
            """
        from typing import Generic, TypeVar
        T = TypeVar('T')
        class A(): ...
        class B(Generic[T]): ...
        class C(A, B[T]): ...
        class D: ...
        class E(C[str], D): ...
        """
        )
        assert isinstance(cls, nodes.ClassDef)
        self.assertEqualMroQName(
            cls, [".E", ".C", ".A", ".B", "typing.Generic", ".D", "builtins.object"]
        )

    def test_mro_generic_error_1(self):
        cls = builder.extract_node(
            """
        from typing import Generic, TypeVar
        T1 = TypeVar('T1')
        T2 = TypeVar('T2')
        class A(Generic[T1], Generic[T2]): ...
        """
        )
        assert isinstance(cls, nodes.ClassDef)
        with self.assertRaises(DuplicateBasesError):
            cls.mro()

    def test_mro_generic_error_2(self):
        cls = builder.extract_node(
            """
        from typing import Generic, TypeVar
        T = TypeVar('T')
        class A(Generic[T]): ...
        class B(A[T], A[T]): ...
        """
        )
        assert isinstance(cls, nodes.ClassDef)
        with self.assertRaises(DuplicateBasesError):
            cls.mro()

    def test_mro_typing_extensions(self):
        """Regression test for mro() inference on typing_extensions.

        Regression reported in:
        https://github.com/pylint-dev/astroid/issues/1124
        """
        module = parse(
            """
        import abc
        import typing
        import dataclasses
        from typing import Protocol

        T = typing.TypeVar("T")

        class MyProtocol(Protocol): pass
        class EarlyBase(typing.Generic[T], MyProtocol): pass
        class Base(EarlyBase[T], abc.ABC): pass
        class Final(Base[object]): pass
        """
        )
        class_names = [
            "ABC",
            "Base",
            "EarlyBase",
            "Final",
            "Generic",
            "MyProtocol",
            "Protocol",
            "object",
        ]
        final_def = module.body[-1]
        self.assertEqual(class_names, sorted(i.name for i in final_def.mro()))

    def test_generator_from_infer_call_result_parent(self) -> None:
        func = builder.extract_node(
            """
        import contextlib

        @contextlib.contextmanager
        def test(): #@
            yield
        """
        )
        assert isinstance(func, nodes.FunctionDef)
        result = next(func.infer_call_result(None))
        self.assertIsInstance(result, Generator)
        self.assertEqual(result.parent, func)

    def test_type_three_arguments(self) -> None:
        classes = builder.extract_node(
            """
        type('A', (object, ), {"a": 1, "b": 2, missing: 3}) #@
        """
        )
        assert isinstance(classes, nodes.Call)
        first = next(classes.infer())
        self.assertIsInstance(first, nodes.ClassDef)
        self.assertEqual(first.name, "A")
        self.assertEqual(first.basenames, ["object"])
        self.assertIsInstance(first["a"], nodes.Const)
        self.assertEqual(first["a"].value, 1)
        self.assertIsInstance(first["b"], nodes.Const)
        self.assertEqual(first["b"].value, 2)
        with self.assertRaises(AttributeInferenceError):
            first.getattr("missing")

    def test_implicit_metaclass(self) -> None:
        cls = builder.extract_node(
            """
        class A(object):
            pass
        """
        )
        assert isinstance(cls, nodes.ClassDef)
        type_cls = nodes.builtin_lookup("type")[1][0]
        self.assertEqual(cls.implicit_metaclass(), type_cls)

    def test_implicit_metaclass_lookup(self) -> None:
        cls = builder.extract_node(
            """
        class A(object):
            pass
        """
        )
        assert isinstance(cls, nodes.ClassDef)
        instance = cls.instantiate_class()
        func = cls.getattr("mro")
        self.assertEqual(len(func), 1)
        self.assertRaises(AttributeInferenceError, instance.getattr, "mro")

    def test_metaclass_lookup_using_same_class(self) -> None:
        """Check that we don't have recursive attribute access for metaclass."""
        cls = builder.extract_node(
            """
        class A(object): pass
        """
        )
        assert isinstance(cls, nodes.ClassDef)
        self.assertEqual(len(cls.getattr("mro")), 1)

    def test_metaclass_lookup_inference_errors(self) -> None:
        module = builder.parse(
            """
        class Metaclass(type):
            foo = lala

        class B(object, metaclass=Metaclass): pass
        """
        )
        cls = module["B"]
        self.assertEqual(util.Uninferable, next(cls.igetattr("foo")))

    def test_metaclass_lookup(self) -> None:
        module = builder.parse(
            """
        class Metaclass(type):
            foo = 42
            @classmethod
            def class_method(cls):
                pass
            def normal_method(cls):
                pass
            @property
            def meta_property(cls):
                return 42
            @staticmethod
            def static():
                pass

        class A(object, metaclass=Metaclass):
            pass
        """
        )
        acls = module["A"]
        normal_attr = next(acls.igetattr("foo"))
        self.assertIsInstance(normal_attr, nodes.Const)
        self.assertEqual(normal_attr.value, 42)

        class_method = next(acls.igetattr("class_method"))
        self.assertIsInstance(class_method, BoundMethod)
        self.assertEqual(class_method.bound, module["Metaclass"])

        normal_method = next(acls.igetattr("normal_method"))
        self.assertIsInstance(normal_method, BoundMethod)
        self.assertEqual(normal_method.bound, module["A"])

        # Attribute access for properties:
        #   from the metaclass is a property object
        #   from the class that uses the metaclass, the value
        #   of the property
        property_meta = next(module["Metaclass"].igetattr("meta_property"))
        self.assertIsInstance(property_meta, objects.Property)
        wrapping = nodes.get_wrapping_class(property_meta)
        self.assertEqual(wrapping, module["Metaclass"])

        property_class = next(acls.igetattr("meta_property"))
        self.assertIsInstance(property_class, nodes.Const)
        self.assertEqual(property_class.value, 42)

        static = next(acls.igetattr("static"))
        self.assertIsInstance(static, nodes.FunctionDef)

    def test_local_attr_invalid_mro(self) -> None:
        cls = builder.extract_node(
            """
        # A has an invalid MRO, local_attr should fallback
        # to using .ancestors.
        class A(object, object):
            test = 42
        class B(A): #@
            pass
        """
        )
        assert isinstance(cls, nodes.ClassDef)
        local = cls.local_attr("test")[0]
        inferred = next(local.infer())
        self.assertIsInstance(inferred, nodes.Const)
        self.assertEqual(inferred.value, 42)

    def test_has_dynamic_getattr(self) -> None:
        module = builder.parse(
            """
        class Getattr(object):
            def __getattr__(self, attrname):
                pass

        class Getattribute(object):
            def __getattribute__(self, attrname):
                pass

        class ParentGetattr(Getattr):
            pass
        """
        )
        self.assertTrue(module["Getattr"].has_dynamic_getattr())
        self.assertTrue(module["Getattribute"].has_dynamic_getattr())
        self.assertTrue(module["ParentGetattr"].has_dynamic_getattr())

        # Test that objects analyzed through the live introspection
        # aren't considered to have dynamic getattr implemented.
        astroid_builder = builder.AstroidBuilder()
        module = astroid_builder.module_build(difflib)
        self.assertFalse(module["SequenceMatcher"].has_dynamic_getattr())

    def test_duplicate_bases_namedtuple(self) -> None:
        module = builder.parse(
            """
        import collections
        _A = collections.namedtuple('A', 'a')

        class A(_A): pass

        class B(A): pass
        """
        )
        names = ["B", "A", "A", "tuple", "object"]
        mro = module["B"].mro()
        class_names = [i.name for i in mro]
        self.assertEqual(names, class_names)

    def test_instance_bound_method_lambdas(self) -> None:
        ast_nodes = builder.extract_node(
            """
        class Test(object): #@
            lam = lambda self: self
            not_method = lambda xargs: xargs
        Test() #@
        """
        )
        assert isinstance(ast_nodes, list)
        cls = next(ast_nodes[0].infer())
        self.assertIsInstance(next(cls.igetattr("lam")), nodes.Lambda)
        self.assertIsInstance(next(cls.igetattr("not_method")), nodes.Lambda)

        instance = next(ast_nodes[1].infer())
        lam = next(instance.igetattr("lam"))
        self.assertIsInstance(lam, BoundMethod)
        not_method = next(instance.igetattr("not_method"))
        self.assertIsInstance(not_method, nodes.Lambda)

    def test_instance_bound_method_lambdas_2(self) -> None:
        """
        Test the fact that a method which is a lambda built from
        a factory is well inferred as a bound method (bug pylint 2594).
        """
        ast_nodes = builder.extract_node(
            """
        def lambda_factory():
            return lambda self: print("Hello world")

        class MyClass(object): #@
            f2 = lambda_factory()

        MyClass() #@
        """
        )
        assert isinstance(ast_nodes, list)
        cls = next(ast_nodes[0].infer())
        self.assertIsInstance(next(cls.igetattr("f2")), nodes.Lambda)

        instance = next(ast_nodes[1].infer())
        f2 = next(instance.igetattr("f2"))
        self.assertIsInstance(f2, BoundMethod)

    def test_class_extra_decorators_frame_is_not_class(self) -> None:
        ast_node = builder.extract_node(
            """
        def ala():
            def bala(): #@
                func = 42
        """
        )
        assert isinstance(ast_node, nodes.FunctionDef)
        self.assertEqual(ast_node.extra_decorators, [])

    def test_class_extra_decorators_only_callfunc_are_considered(self) -> None:
        ast_node = builder.extract_node(
            """
        class Ala(object):
             def func(self): #@
                 pass
             func = 42
        """
        )
        self.assertEqual(ast_node.extra_decorators, [])

    def test_class_extra_decorators_only_assignment_names_are_considered(self) -> None:
        ast_node = builder.extract_node(
            """
        class Ala(object):
             def func(self): #@
                 pass
             def __init__(self):
                 self.func = staticmethod(func)

        """
        )
        self.assertEqual(ast_node.extra_decorators, [])

    def test_class_extra_decorators_only_same_name_considered(self) -> None:
        ast_node = builder.extract_node(
            """
        class Ala(object):
             def func(self): #@
                pass
             bala = staticmethod(func)
        """
        )
        self.assertEqual(ast_node.extra_decorators, [])
        self.assertEqual(ast_node.type, "method")

    def test_class_extra_decorators(self) -> None:
        static_method, clsmethod = builder.extract_node(
            """
        class Ala(object):
             def static(self): #@
                 pass
             def class_method(self): #@
                 pass
             class_method = classmethod(class_method)
             static = staticmethod(static)
        """
        )
        self.assertEqual(len(clsmethod.extra_decorators), 1)
        self.assertEqual(clsmethod.type, "classmethod")
        self.assertEqual(len(static_method.extra_decorators), 1)
        self.assertEqual(static_method.type, "staticmethod")

    def test_extra_decorators_only_class_level_assignments(self) -> None:
        node = builder.extract_node(
            """
        def _bind(arg):
            return arg.bind

        class A(object):
            @property
            def bind(self):
                return 42
            def irelevant(self):
                # This is important, because it used to trigger
                # a maximum recursion error.
                bind = _bind(self)
                return bind
        A() #@
        """
        )
        inferred = next(node.infer())
        bind = next(inferred.igetattr("bind"))
        self.assertIsInstance(bind, nodes.Const)
        self.assertEqual(bind.value, 42)
        parent = bind.scope()
        self.assertEqual(len(parent.extra_decorators), 0)

    def test_class_keywords(self) -> None:
        data = """
            class TestKlass(object, metaclass=TestMetaKlass,
                    foo=42, bar='baz'):
                pass
        """
        astroid = builder.parse(data, __name__)
        cls = astroid["TestKlass"]
        self.assertEqual(len(cls.keywords), 2)
        self.assertEqual([x.arg for x in cls.keywords], ["foo", "bar"])
        children = list(cls.get_children())
        assert len(children) == 4
        assert isinstance(children[1], nodes.Keyword)
        assert isinstance(children[2], nodes.Keyword)
        assert children[1].arg == "foo"
        assert children[2].arg == "bar"

    def test_kite_graph(self) -> None:
        data = """
        A = type('A', (object,), {})

        class B1(A): pass

        class B2(A): pass

        class C(B1, B2): pass

        class D(C):
            def update(self):
                self.hello = 'hello'
        """
        # Should not crash
        builder.parse(data)

    @staticmethod
    def test_singleline_docstring() -> None:
        code = textwrap.dedent(
            """\
            class Foo:
                '''Hello World'''
                bar = 1
        """
        )
        node: nodes.ClassDef = builder.extract_node(code)  # type: ignore[assignment]
        assert isinstance(node.doc_node, nodes.Const)
        assert node.doc_node.lineno == 2
        assert node.doc_node.col_offset == 4
        assert node.doc_node.end_lineno == 2
        assert node.doc_node.end_col_offset == 21

    @staticmethod
    def test_multiline_docstring() -> None:
        code = textwrap.dedent(
            """\
            class Foo:
                '''Hello World

                Also on this line.
                '''
                bar = 1
        """
        )
        node: nodes.ClassDef = builder.extract_node(code)  # type: ignore[assignment]
        assert isinstance(node.doc_node, nodes.Const)
        assert node.doc_node.lineno == 2
        assert node.doc_node.col_offset == 4
        assert node.doc_node.end_lineno == 5
        assert node.doc_node.end_col_offset == 7

    @staticmethod
    def test_without_docstring() -> None:
        code = textwrap.dedent(
            """\
            class Foo:
                bar = 1
        """
        )
        node: nodes.ClassDef = builder.extract_node(code)  # type: ignore[assignment]
        assert node.doc_node is None


def test_issue940_metaclass_subclass_property() -> None:
    node = builder.extract_node(
        """
    class BaseMeta(type):
        @property
        def __members__(cls):
            return ['a', 'property']
    class Parent(metaclass=BaseMeta):
        pass
    class Derived(Parent):
        pass
    Derived.__members__
    """
    )
    inferred = next(node.infer())
    assert isinstance(inferred, nodes.List)
    assert [c.value for c in inferred.elts] == ["a", "property"]


def test_issue940_property_grandchild() -> None:
    node = builder.extract_node(
        """
    class Grandparent:
        @property
        def __members__(self):
            return ['a', 'property']
    class Parent(Grandparent):
        pass
    class Child(Parent):
        pass
    Child().__members__
    """
    )
    inferred = next(node.infer())
    assert isinstance(inferred, nodes.List)
    assert [c.value for c in inferred.elts] == ["a", "property"]


def test_issue940_metaclass_property() -> None:
    node = builder.extract_node(
        """
    class BaseMeta(type):
        @property
        def __members__(cls):
            return ['a', 'property']
    class Parent(metaclass=BaseMeta):
        pass
    Parent.__members__
    """
    )
    inferred = next(node.infer())
    assert isinstance(inferred, nodes.List)
    assert [c.value for c in inferred.elts] == ["a", "property"]


def test_issue940_with_metaclass_class_context_property() -> None:
    node = builder.extract_node(
        """
    class BaseMeta(type):
        pass
    class Parent(metaclass=BaseMeta):
        @property
        def __members__(self):
            return ['a', 'property']
    class Derived(Parent):
        pass
    Derived.__members__
    """
    )
    inferred = next(node.infer())
    assert not isinstance(inferred, nodes.List)
    assert isinstance(inferred, objects.Property)


def test_issue940_metaclass_values_funcdef() -> None:
    node = builder.extract_node(
        """
    class BaseMeta(type):
        def __members__(cls):
            return ['a', 'func']
    class Parent(metaclass=BaseMeta):
        pass
    Parent.__members__()
    """
    )
    inferred = next(node.infer())
    assert isinstance(inferred, nodes.List)
    assert [c.value for c in inferred.elts] == ["a", "func"]


def test_issue940_metaclass_derived_funcdef() -> None:
    node = builder.extract_node(
        """
    class BaseMeta(type):
        def __members__(cls):
            return ['a', 'func']
    class Parent(metaclass=BaseMeta):
        pass
    class Derived(Parent):
        pass
    Derived.__members__()
    """
    )
    inferred_result = next(node.infer())
    assert isinstance(inferred_result, nodes.List)
    assert [c.value for c in inferred_result.elts] == ["a", "func"]


def test_issue940_metaclass_funcdef_is_not_datadescriptor() -> None:
    node = builder.extract_node(
        """
    class BaseMeta(type):
        def __members__(cls):
            return ['a', 'property']
    class Parent(metaclass=BaseMeta):
        @property
        def __members__(cls):
            return BaseMeta.__members__()
    class Derived(Parent):
        pass
    Derived.__members__
    """
    )
    # Here the function is defined on the metaclass, but the property
    # is defined on the base class. When loading the attribute in a
    # class context, this should return the property object instead of
    # resolving the data descriptor
    inferred = next(node.infer())
    assert isinstance(inferred, objects.Property)


def test_property_in_body_of_try() -> None:
    """Regression test for https://github.com/pylint-dev/pylint/issues/6596."""
    node: nodes.Return = builder._extract_single_node(
        """
    def myfunc():
        try:

            @property
            def myfunc():
                return None

        except TypeError:
            pass

        @myfunc.setter
        def myfunc():
            pass

        return myfunc() #@
    """
    )
    next(node.value.infer())


def test_property_in_body_of_if() -> None:
    node: nodes.Return = builder._extract_single_node(
        """
    def myfunc():
        if True:

            @property
            def myfunc():
                return None

        @myfunc.setter
        def myfunc():
            pass

        return myfunc() #@
    """
    )
    next(node.value.infer())


def test_issue940_enums_as_a_real_world_usecase() -> None:
    node = builder.extract_node(
        """
    from enum import Enum
    class Sounds(Enum):
        bee = "buzz"
        cat = "meow"
    Sounds.__members__
    """
    )
    inferred_result = next(node.infer())
    assert isinstance(inferred_result, nodes.Dict)
    actual = [k.value for k, _ in inferred_result.items]
    assert sorted(actual) == ["bee", "cat"]


def test_enums_type_annotation_str_member() -> None:
    """A type-annotated member of an Enum class where:
    - `member.value` is of type `nodes.Const` &
    - `member.value.value` is of type `str`
    is inferred as: `repr(member.value.value)`
    """
    node = builder.extract_node(
        """
    from enum import Enum
    class Veg(Enum):
        TOMATO: str = "sweet"

    Veg.TOMATO.value
    """
    )
    inferred_member_value = node.inferred()[0]
    assert isinstance(inferred_member_value, nodes.Const)
    assert inferred_member_value.value == "sweet"


@pytest.mark.parametrize("annotation", ["bool", "dict", "int", "str"])
def test_enums_type_annotation_no_value(annotation) -> None:
    """A type-annotated member of an Enum class which has no value where:
    - `member.value.value` is `None`
    is not inferred
    """
    node = builder.extract_node(
        """
    from enum import Enum
    class Veg(Enum):
        TOMATO: {annotation}

    Veg.TOMATO.value
    """
    )
    inferred_member_value = node.inferred()[0]
    assert inferred_member_value.value is None


def test_enums_value2member_map_() -> None:
    """Check the `_value2member_map_` member is present in an Enum class."""
    node = builder.extract_node(
        """
    from enum import Enum
    class Veg(Enum):
        TOMATO: 1

    Veg
    """
    )
    inferred_class = node.inferred()[0]
    assert "_value2member_map_" in inferred_class.locals


@pytest.mark.parametrize("annotation, value", [("int", 42), ("bytes", b"")])
def test_enums_type_annotation_non_str_member(annotation, value) -> None:
    """A type-annotated member of an Enum class where:
    - `member.value` is of type `nodes.Const` &
    - `member.value.value` is not of type `str`
    is inferred as: `member.value.value`
    """

    node = builder.extract_node(
        f"""
    from enum import Enum
    class Veg(Enum):
        TOMATO: {annotation} = {value}

    Veg.TOMATO.value
    """
    )
    inferred_member_value = node.inferred()[0]
    assert isinstance(inferred_member_value, nodes.Const)
    assert inferred_member_value.value == value


@pytest.mark.parametrize(
    "annotation, value",
    [
        ("dict", {"variety": "beefeater"}),
        ("list", ["beefeater", "moneymaker"]),
        ("TypedDict", {"variety": "moneymaker"}),
    ],
)
def test_enums_type_annotations_non_const_member(annotation, value) -> None:
    """A type-annotated member of an Enum class where:
    - `member.value` is not of type `nodes.Const`
    is inferred as: `member.value.as_string()`.
    """

    member = builder.extract_node(
        f"""
    from enum import Enum

    class Veg(Enum):
        TOMATO: {annotation} = {value}

    Veg.TOMATO.value
    """
    )

    inferred_member_value = member.inferred()[0]
    assert not isinstance(inferred_member_value, nodes.Const)
    assert inferred_member_value.as_string() == repr(value)


def test_metaclass_cannot_infer_call_yields_an_instance() -> None:
    node = builder.extract_node(
        """
    from undefined import Undefined
    class Meta(type):
        __call__ = Undefined
    class A(metaclass=Meta):
        pass
    A()
    """
    )
    inferred = next(node.infer())
    assert isinstance(inferred, Instance)


@pytest.mark.parametrize(
    "func",
    [
        textwrap.dedent(
            """
    def func(a, b, /, d, e):
        pass
    """
        ),
        textwrap.dedent(
            """
    def func(a, b=None, /, d=None, e=None):
        pass
    """
        ),
        textwrap.dedent(
            """
    def func(a, other, other, b=None, /, d=None, e=None):
        pass
    """
        ),
        textwrap.dedent(
            """
    def func(a, other, other, b=None, /, d=None, e=None, **kwargs):
        pass
    """
        ),
        textwrap.dedent(
            """
    def name(p1, p2, /, p_or_kw, *, kw):
        pass
    """
        ),
        textwrap.dedent(
            """
    def __init__(self, other=(), /, **kw):
        pass
    """
        ),
        textwrap.dedent(
            """
    def __init__(self: int, other: float, /, **kw):
        pass
    """
        ),
    ],
)
def test_posonlyargs_python_38(func):
    ast_node = builder.extract_node(func)
    assert ast_node.as_string().strip() == func.strip()


def test_posonlyargs_default_value() -> None:
    ast_node = builder.extract_node(
        """
    def func(a, b=1, /, c=2): pass
    """
    )
    last_param = ast_node.args.default_value("c")
    assert isinstance(last_param, nodes.Const)
    assert last_param.value == 2

    first_param = ast_node.args.default_value("b")
    assert isinstance(first_param, nodes.Const)
    assert first_param.value == 1


def test_ancestor_with_generic() -> None:
    # https://github.com/pylint-dev/astroid/issues/942
    tree = builder.parse(
        """
    from typing import TypeVar, Generic
    T = TypeVar("T")
    class A(Generic[T]):
        def a_method(self):
            print("hello")
    class B(A[T]): pass
    class C(B[str]): pass
    """
    )
    inferred_b = next(tree["B"].infer())
    assert [cdef.name for cdef in inferred_b.ancestors()] == ["A", "Generic", "object"]

    inferred_c = next(tree["C"].infer())
    assert [cdef.name for cdef in inferred_c.ancestors()] == [
        "B",
        "A",
        "Generic",
        "object",
    ]


def test_slots_duplicate_bases_issue_1089() -> None:
    astroid = builder.parse(
        """
            class First(object, object): #@
                pass
        """
    )
    with pytest.raises(NotImplementedError):
        astroid["First"].slots()


class TestFrameNodes:
    @staticmethod
    def test_frame_node():
        """Test if the frame of FunctionDef, ClassDef and Module is correctly set."""
        module = builder.parse(
            """
            def func():
                var_1 = x
                return var_1

            class MyClass:

                attribute = 1

                def method():
                    pass

            VAR = lambda y = (named_expr := "walrus"): print(y)
        """
        )
        function = module.body[0]
        assert function.frame() == function
        assert function.frame() == function
        assert function.body[0].frame() == function
        assert function.body[0].frame() == function

        class_node = module.body[1]
        assert class_node.frame() == class_node
        assert class_node.frame() == class_node
        assert class_node.body[0].frame() == class_node
        assert class_node.body[0].frame() == class_node
        assert class_node.body[1].frame() == class_node.body[1]
        assert class_node.body[1].frame() == class_node.body[1]

        lambda_assignment = module.body[2].value
        assert lambda_assignment.args.args[0].frame() == lambda_assignment
        assert lambda_assignment.args.args[0].frame() == lambda_assignment

        assert module.frame() == module
        assert module.frame() == module

    @staticmethod
    def test_non_frame_node():
        """Test if the frame of non frame nodes is set correctly."""
        module = builder.parse(
            """
            VAR_ONE = 1

            VAR_TWO = [x for x in range(1)]
        """
        )
        assert module.body[0].frame() == module
        assert module.body[0].frame() == module

        assert module.body[1].value.locals["x"][0].frame() == module
        assert module.body[1].value.locals["x"][0].frame() == module
