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
import tempfile
import textwrap
import unittest
from functools import partial
from typing import Any
from unittest.mock import patch

import pytest

from astroid import (
    MANAGER,
    builder,
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
    NoDefault,
    ResolveError,
    TooManyLevelsError,
)
from astroid.manager import AstroidManager
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
        m = builder.parse("""
        name = 'a'
        _bla = 2
        other = 'o'
        class Aaa: pass
        def func(): print('yo')
        __all__ = 'Aaa', '_bla', 'name'
        """)
        values = sorted(["Aaa", "name", "other", "func"])
        self.assertEqual(sorted(m.public_names()), values)
        m = builder.parse("""
        name = 'a'
        _bla = 2
        other = 'o'
        class Aaa: pass

        def func(): return 'yo'
        """)
        res = sorted(m.public_names())
        self.assertEqual(res, values)

        m = builder.parse("""
            from missing import tzop
            trop = "test"
            __all__ = (trop, "test1", tzop, 42)
        """)
        res = sorted(m.public_names())
        self.assertEqual(res, ["trop", "tzop"])

        m = builder.parse("""
            test = tzop = 42
            __all__ = ('test', ) + ('tzop', )
        """)
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
        astroid = builder.AstroidBuilder(AstroidManager()).file_build(path, "all")
        with open(path, "rb") as file_io:
            with astroid.stream() as stream:
                self.assertEqual(stream.read(), file_io.read())

    def test_file_stream_api(self) -> None:
        path = resources.find("data/all.py")
        file_build = builder.AstroidBuilder(AstroidManager()).file_build(path, "all")
        with self.assertRaises(AttributeError):
            # pylint: disable=pointless-statement, no-member
            file_build.file_stream  # noqa: B018

    def test_stream_api(self) -> None:
        path = resources.find("data/all.py")
        astroid = builder.AstroidBuilder(AstroidManager()).file_build(path, "all")
        stream = astroid.stream()
        self.assertTrue(hasattr(stream, "close"))
        with stream:
            with open(path, "rb") as file_io:
                self.assertEqual(stream.read(), file_io.read())

    @staticmethod
    def test_singleline_docstring() -> None:
        data = textwrap.dedent("""\
            '''Hello World'''
            foo = 1
        """)
        module = builder.parse(data, __name__)
        assert isinstance(module.doc_node, nodes.Const)
        assert module.doc_node.lineno == 1
        assert module.doc_node.col_offset == 0
        assert module.doc_node.end_lineno == 1
        assert module.doc_node.end_col_offset == 17

    @staticmethod
    def test_multiline_docstring() -> None:
        data = textwrap.dedent("""\
            '''Hello World

            Also on this line.
            '''
            foo = 1
        """)
        module = builder.parse(data, __name__)

        assert isinstance(module.doc_node, nodes.Const)
        assert module.doc_node.lineno == 1
        assert module.doc_node.col_offset == 0
        assert module.doc_node.end_lineno == 4
        assert module.doc_node.end_col_offset == 3

    @staticmethod
    def test_comment_before_docstring() -> None:
        data = textwrap.dedent("""\
            # Some comment
            '''This is

            a multiline docstring.
            '''
        """)
        module = builder.parse(data, __name__)

        assert isinstance(module.doc_node, nodes.Const)
        assert module.doc_node.lineno == 2
        assert module.doc_node.col_offset == 0
        assert module.doc_node.end_lineno == 5
        assert module.doc_node.end_col_offset == 3

    @staticmethod
    def test_without_docstring() -> None:
        data = textwrap.dedent("""\
            foo = 1
        """)
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
        node = builder.parse("""
        def test(a: int, *, b: dict):
            pass
        """).body[-1].args
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
        methods = builder.extract_node("""
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

    def test_comprehension_qname(self) -> None:
        module = builder.parse(
            """
            def func():
                (x for x in y)
                [x for x in y]
                {x for x in y}
                {x: x for x in y}
            """,
            __name__,
        )
        names = [stmt.value.qname() for stmt in module["func"].body]
        self.assertEqual(
            names,
            [
                f"{__name__}.func.<genexpr>",
                f"{__name__}.func.<listcomp>",
                f"{__name__}.func.<setcomp>",
                f"{__name__}.func.<dictcomp>",
            ],
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

    def test_func_getattr_does_not_modify_instance_attrs(self) -> None:
        """Looking up an attribute that is also a special attribute must not
        add the special attribute to instance_attrs.
        """
        func = builder.extract_node("""
            def func():
                pass

            func.__name__ = "name"
            func #@
        """).inferred()[0]
        self.assertIsInstance(func, nodes.FunctionDef)
        lambda_func = builder.extract_node("lambda: None")
        lambda_func.instance_attrs["__name__"] = [nodes.Const("name")]
        for node in (func, lambda_func):
            self.assertEqual(len(node.getattr("__name__")), 2)
            self.assertEqual(len(node.getattr("__name__")), 2)
            self.assertEqual(len(node.instance_attrs["__name__"]), 1)

    def test_type_builtin_descriptor_subclasses(self) -> None:
        astroid = builder.parse("""
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
        node = astroid.locals["Node"][0]
        self.assertEqual(node.locals["clsmethod_subclass"][0].type, "classmethod")
        self.assertEqual(node.locals["clsmethod"][0].type, "classmethod")
        self.assertEqual(node.locals["staticmethod_subclass"][0].type, "staticmethod")
        self.assertEqual(node.locals["stcmethod"][0].type, "staticmethod")

    def test_decorator_builtin_descriptors(self) -> None:
        astroid = builder.parse("""
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
        node = astroid.locals["SomeClass"][0]
        self.assertEqual(node.locals["static"][0].type, "staticmethod")
        self.assertEqual(node.locals["classmethod"][0].type, "classmethod")
        self.assertEqual(node.locals["not_so_static"][0].type, "method")
        self.assertEqual(node.locals["not_so_classmethod"][0].type, "method")
        self.assertEqual(node.locals["classmethod_wrapped"][0].type, "classmethod")
        self.assertEqual(node.locals["staticmethod_wrapped"][0].type, "staticmethod")
        self.assertEqual(node.locals["long_classmethod"][0].type, "classmethod")

    def test_igetattr(self) -> None:
        func = builder.extract_node("""
        def test():
            pass
        """)
        assert isinstance(func, nodes.FunctionDef)
        func.instance_attrs["value"] = [nodes.Const(42)]
        value = func.getattr("value")
        self.assertEqual(len(value), 1)
        self.assertIsInstance(value[0], nodes.Const)
        self.assertEqual(value[0].value, 42)
        inferred = next(func.igetattr("value"))
        self.assertIsInstance(inferred, nodes.Const)
        self.assertEqual(inferred.value, 42)


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
        node = builder.extract_node("""
        class A(object): pass
        class B(object): pass
        class C(A, B): pass
        """)
        assert isinstance(node, nodes.ClassDef)
        mro = node.getattr("__mro__")[0]
        self.assertIsInstance(mro, nodes.Tuple)
        self.assertEqual(mro.elts, node.mro())

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
        module = builder.parse("""
        class A():
            def __init__(self): pass
        class B(A): pass
        class C(B): pass
        class D(object): pass
        class F(): pass
        class E(F, D): pass
        """)
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

    def test_no_infinite_metaclass_loop(self) -> None:
        klass = builder.extract_node("""
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
        """)
        assert isinstance(klass, nodes.ClassDef)
        self.assertFalse(_is_metaclass(klass))
        ancestors = [base.name for base in klass.ancestors()]
        self.assertIn("object", ancestors)
        self.assertIn("JJJ", ancestors)

    def test_add_metaclass(self) -> None:
        klass = builder.extract_node("""
        import abc

        class WithMeta(object, metaclass=abc.ABCMeta):
            pass
        """)
        assert isinstance(klass, nodes.ClassDef)
        inferred = next(klass.infer())
        metaclass = inferred.metaclass()
        self.assertIsInstance(metaclass, nodes.ClassDef)
        self.assertIn(metaclass.qname(), ("abc.ABCMeta", "_py_abc.ABCMeta"))

    def test_slots(self) -> None:
        astroid = builder.parse("""
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
        """)
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

    def assertEqualMro(self, klass: nodes.ClassDef, expected_mro: list[str]) -> None:
        self.assertEqual([member.name for member in klass.mro()], expected_mro)

    def assertEqualMroQName(
        self, klass: nodes.ClassDef, expected_mro: list[str]
    ) -> None:
        self.assertEqual([member.qname() for member in klass.mro()], expected_mro)

    def test_mro(self) -> None:
        astroid = builder.parse("""
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

        """)
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

    def test_mro_typing_extensions(self):
        """Regression test for mro() inference on typing_extensions.

        Regression reported in:
        https://github.com/pylint-dev/astroid/issues/1124
        """
        module = parse("""
        import abc
        import typing
        import dataclasses
        from typing import Protocol

        T = typing.TypeVar("T")

        class MyProtocol(Protocol): pass
        class EarlyBase(typing.Generic[T], MyProtocol): pass
        class Base(EarlyBase[T], abc.ABC): pass
        class Final(Base[object]): pass
        """)
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
        func = builder.extract_node("""
        import contextlib

        @contextlib.contextmanager
        def test(): #@
            yield
        """)
        assert isinstance(func, nodes.FunctionDef)
        result = next(func.infer_call_result(None))
        self.assertIsInstance(result, Generator)
        self.assertEqual(result.parent, func)

    def test_implicit_metaclass(self) -> None:
        cls = builder.extract_node("""
        class A(object):
            pass
        """)
        assert isinstance(cls, nodes.ClassDef)
        type_cls = nodes.builtin_lookup("type")[1][0]
        self.assertEqual(cls.implicit_metaclass(), type_cls)

    def test_metaclass_lookup(self) -> None:
        module = builder.parse("""
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
        """)
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

    def test_has_dynamic_getattr(self) -> None:
        module = builder.parse("""
        class Getattr(object):
            def __getattr__(self, attrname):
                pass

        class Getattribute(object):
            def __getattribute__(self, attrname):
                pass

        class ParentGetattr(Getattr):
            pass
        """)
        self.assertTrue(module["Getattr"].has_dynamic_getattr())
        self.assertTrue(module["Getattribute"].has_dynamic_getattr())
        self.assertTrue(module["ParentGetattr"].has_dynamic_getattr())

        # Test that objects analyzed through the live introspection
        # aren't considered to have dynamic getattr implemented.
        astroid_builder = builder.AstroidBuilder(AstroidManager())
        module = astroid_builder.module_build(difflib)
        self.assertFalse(module["SequenceMatcher"].has_dynamic_getattr())

    def test_duplicate_bases_namedtuple(self) -> None:
        module = builder.parse("""
        import collections
        _A = collections.namedtuple('A', 'a')

        class A(_A): pass

        class B(A): pass
        """)
        names = ["B", "A", "A", "tuple", "object"]
        mro = module["B"].mro()
        class_names = [i.name for i in mro]
        self.assertEqual(names, class_names)

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


def test_property_in_body_of_try() -> None:
    """Regression test for https://github.com/pylint-dev/pylint/issues/6596."""
    node: nodes.Return = builder._extract_single_node("""
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
    """)
    next(node.value.infer())


def test_property_in_body_of_if() -> None:
    node: nodes.Return = builder._extract_single_node("""
    def myfunc():
        if True:

            @property
            def myfunc():
                return None

        @myfunc.setter
        def myfunc():
            pass

        return myfunc() #@
    """)
    next(node.value.infer())


def test_issue940_enums_as_a_real_world_usecase() -> None:
    node = builder.extract_node("""
    from enum import Enum
    class Sounds(Enum):
        bee = "buzz"
        cat = "meow"
    Sounds.__members__
    """)
    inferred_result = next(node.infer())
    assert isinstance(inferred_result, nodes.Dict)
    actual = [k.value for k, _ in inferred_result.items]
    assert sorted(actual) == ["bee", "cat"]


@pytest.mark.parametrize("annotation", ["bool", "dict", "int", "str"])
def test_enums_type_annotation_no_value(annotation) -> None:
    """A type-annotated member of an Enum class which has no value where:
    - `member.value.value` is `None`
    is not inferred
    """
    node = builder.extract_node("""
    from enum import Enum
    class Veg(Enum):
        TOMATO: {annotation}

    Veg.TOMATO.value
    """)
    inferred_member_value = node.inferred()[0]
    assert inferred_member_value.value is None


@pytest.mark.parametrize("annotation, value", [("int", 42), ("bytes", b"")])
def test_enums_type_annotation_non_str_member(annotation, value) -> None:
    """A type-annotated member of an Enum class where:
    - `member.value` is of type `nodes.Const` &
    - `member.value.value` is not of type `str`
    is inferred as: `member.value.value`
    """

    node = builder.extract_node(f"""
    from enum import Enum
    class Veg(Enum):
        TOMATO: {annotation} = {value}

    Veg.TOMATO.value
    """)
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

    member = builder.extract_node(f"""
    from enum import Enum

    class Veg(Enum):
        TOMATO: {annotation} = {value}

    Veg.TOMATO.value
    """)

    inferred_member_value = member.inferred()[0]
    assert not isinstance(inferred_member_value, nodes.Const)
    assert inferred_member_value.as_string() == repr(value)


def test_metaclass_call_result_without_context() -> None:
    # Regression: ClassDef.infer_call_result may be called through the public
    # API without a context (it defaults to None). For a class whose metaclass
    # defines __call__, that path set context.callcontext.callee without
    # guarding, crashing with "AttributeError: 'NoneType' object has no
    # attribute 'callee'". It should infer the __call__ result instead.
    call = builder.extract_node("""
    class Meta(type):
        def __call__(cls, *args, **kwargs):
            return 42
    class C(metaclass=Meta):
        pass
    C() #@
    """)
    cls = next(call.func.infer())
    assert isinstance(cls, nodes.ClassDef)
    for caller in (call, None):
        inferred = list(cls.infer_call_result(caller=caller))
        assert [getattr(n, "value", None) for n in inferred] == [42]


def test_type_subclass_call_result_without_caller() -> None:
    # Regression: ClassDef.infer_call_result may be called through the public
    # API without a caller (it accepts None). For a subclass of ``type``, the
    # three-argument ``type(name, bases, dict)`` check read ``caller.args``
    # unguarded, crashing with "AttributeError: 'NoneType' object has no
    # attribute 'args'". It should infer an instance of the metaclass instead.
    node = builder.extract_node("class Meta(type): pass")
    inferred = list(node.infer_call_result(caller=None))
    assert len(inferred) == 1
    assert isinstance(inferred[0], Instance)
    assert inferred[0].qname() == ".Meta"


@pytest.mark.parametrize(
    "func",
    [
        textwrap.dedent("""
    def func(a, b, /, d, e):
        pass
    """),
        textwrap.dedent("""
    def func(a, b=None, /, d=None, e=None):
        pass
    """),
        textwrap.dedent("""
    def func(a, other, other, b=None, /, d=None, e=None):
        pass
    """),
        textwrap.dedent("""
    def func(a, other, other, b=None, /, d=None, e=None, **kwargs):
        pass
    """),
        textwrap.dedent("""
    def name(p1, p2, /, p_or_kw, *, kw):
        pass
    """),
        textwrap.dedent("""
    def __init__(self, other=(), /, **kw):
        pass
    """),
        textwrap.dedent("""
    def __init__(self: int, other: float, /, **kw):
        pass
    """),
    ],
)
def test_posonlyargs_python_38(func):
    ast_node = builder.extract_node(func)
    assert ast_node.as_string().strip() == func.strip()


def test_classdef_repr_tree_ast_state() -> None:
    node = builder.extract_node("class A: pass")
    assert "locals=" in node.repr_tree(ast_state=True)


def test_import_with_global() -> None:
    code = builder.parse("""
    def f1():
        global platform
        from sys import platform as plat
        platform = plat

    def f2():
        global os, RE, deque, VERSION, Path
        import os
        import re as RE
        from collections import deque
        from sys import version as VERSION
        from pathlib import *
    """)
    assert "platform" in code.locals
    assert "os" in code.locals
    assert "RE" in code.locals
    assert "deque" in code.locals
    assert "VERSION" in code.locals
    assert "Path" in code.locals


class StubScopedNodeTest(unittest.TestCase):
    def test_stub_class_getattr_annassign(self) -> None:
        module = builder.parse(
            """
            class Foo:
                x: int
            """,
            is_stub=True,
        )
        cls = module.body[0]
        assert isinstance(cls, nodes.ClassDef)
        attrs = cls.getattr("x")
        assert len(attrs) == 1

    def test_nonstub_class_getattr_skips_bare_annassign(self) -> None:
        module = builder.parse("""
            class Foo:
                x: int
            """)
        cls = module.body[0]
        assert isinstance(cls, nodes.ClassDef)
        with self.assertRaises(AttributeInferenceError):
            cls.getattr("x")

    def test_nonstub_subclass_inherits_stub_annassign(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            stub_path = os.path.join(tmp_dir, "stubbase.pyi")
            with open(stub_path, "w", encoding="utf-8") as file:
                file.write("class Base:\n    color: str\n")
            with resources.augmented_sys_path([tmp_dir]):
                node = builder.extract_node(
                    """
                    from stubbase import Base
                    class Sub(Base): ...
                    Sub().color  #@
                    """,
                    module_name="user_mod",
                )
                inferred = next(node.infer())
        assert isinstance(inferred, Instance)
        assert inferred.name == "str"

    def test_stub_subclass_skips_nonstub_annassign(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            source_path = os.path.join(tmp_dir, "sourcebase.py")
            with open(source_path, "w", encoding="utf-8") as file:
                file.write("class Base:\n    color: str\n")
            with resources.augmented_sys_path([tmp_dir]):
                module = builder.parse(
                    "from sourcebase import Base\nclass Sub(Base): ...",
                    module_name="stub_mod",
                    is_stub=True,
                )
                subclass = module.body[1]
                assert isinstance(subclass, nodes.ClassDef)
                with self.assertRaises(AttributeInferenceError):
                    subclass.getattr("color")

    def test_stub_funcdef_infer_call_result_int(self) -> None:
        module = builder.parse("def f() -> int: ...", is_stub=True)
        func = module.body[0]
        results = list(func.infer_call_result(None))
        assert len(results) == 1
        assert isinstance(results[0], Instance)
        assert results[0].name == "int"

    def test_stub_funcdef_pass_infers_return_annotation(self) -> None:
        module = builder.parse("def f() -> int: pass", is_stub=True)
        func = module.body[0]
        results = list(func.infer_call_result(None))
        assert len(results) == 1
        assert isinstance(results[0], Instance)
        assert results[0].name == "int"

    def test_stub_docstring_only_infers_return_annotation(self) -> None:
        for prefix in ("def", "async def"):
            with self.subTest(prefix=prefix):
                module = builder.parse(
                    f'{prefix} f() -> str:\n    """Documentation"""',
                    is_stub=True,
                )
                func = module.body[0]
                assert func.body == []
                assert isinstance(func.doc_node, nodes.Const)
                assert func.doc_node.value == "Documentation"
                results = list(func.infer_call_result(None))
                assert len(results) == 1
                assert isinstance(results[0], Instance)
                assert results[0].name == "str"
                compile(module.as_string(), "<stub>", "exec")

    def test_stub_docstring_only_without_annotation_is_uninferable(self) -> None:
        module = builder.parse('def f():\n    """Documentation"""', is_stub=True)
        assert list(module.body[0].infer_call_result(None)) == [util.Uninferable]

    def test_stub_docstring_only_property_infers_annotation(self) -> None:
        module = builder.parse(
            '''
            class Validator:
                @property
                def title(self) -> str:
                    """The title of the schema"""
            value = Validator().title
            ''',
            is_stub=True,
        )
        result = next(module.locals["value"][0].infer())
        assert isinstance(result, Instance)
        assert result.name == "str"

    def test_nonstub_docstring_only_inference_is_unchanged(self) -> None:
        module = builder.parse('def f() -> str:\n    """Documentation"""')
        with self.assertRaises(InferenceError):
            list(module.body[0].infer_call_result(None))

    def test_stub_funcdef_non_placeholder_body_has_implicit_none_return(self) -> None:
        module = builder.parse("def f() -> int:\n    x = 1\n    x", is_stub=True)
        func = module.body[0]
        results = list(func.infer_call_result(None))
        assert len(results) == 1
        assert isinstance(results[0], nodes.Const)
        assert results[0].value is None

    def test_stub_funcdef_infer_call_result_none(self) -> None:
        module = builder.parse("def f() -> None: ...", is_stub=True)
        func = module.body[0]
        results = list(func.infer_call_result(None))
        assert len(results) == 1
        assert isinstance(results[0], nodes.Const)
        assert results[0].value is None

    def test_stub_funcdef_no_return_annotation(self) -> None:
        module = builder.parse("def f(): ...", is_stub=True)
        func = module.body[0]
        results = list(func.infer_call_result(None))
        assert len(results) == 1
        assert results[0] is util.Uninferable

    def test_stub_funcdef_forward_ref_return(self) -> None:
        module = builder.parse(
            """
            class Parser:
                @classmethod
                def create(cls) -> "Parser": ...
            """,
            is_stub=True,
        )
        cls = module.body[0]
        method = cls.body[0]
        results = list(method.infer_call_result(None))
        assert len(results) == 1
        assert isinstance(results[0], Instance)
        assert results[0].name == "Parser"

    def test_stub_funcdef_unresolvable_forward_ref(self) -> None:
        module = builder.parse(
            'def f() -> "DoesNotExist": ...',
            module_name="stub_mod",
            is_stub=True,
        )
        func = module.body[0]
        results = list(func.infer_call_result(None))
        assert len(results) == 1
        assert results[0] is util.Uninferable

    def test_nonstub_funcdef_ellipsis_infer_uninferable(self) -> None:
        """Outside a stub module, the annotation is not used to infer the result."""
        module = builder.parse("def f() -> int: ...")
        func = module.body[0]
        results = list(func.infer_call_result(None))
        assert results == [util.Uninferable]


class TestFrameNodes:
    @staticmethod
    def test_frame_node():
        """Test if the frame of FunctionDef, ClassDef and Module is correctly set."""
        module = builder.parse("""
            def func():
                var_1 = x
                return var_1

            class MyClass:

                attribute = 1

                def method():
                    pass

            VAR = lambda y = (named_expr := "walrus"): print(y)
        """)
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
    def test_frame_node_for_decorators():
        code = builder.extract_node("""
            def deco(var):
                def inner(arg):
                    ...
                return inner

            @deco(
                x := 1  #@
            )
            def func():  #@
                ...

            @deco(
                y := 2  #@
            )
            class A:  #@
                ...
        """)
        name_expr_node1, func_node, name_expr_node2, class_node = code
        module = func_node.root()
        assert name_expr_node1.scope() == module
        assert name_expr_node1.frame() == module
        assert name_expr_node2.scope() == module
        assert name_expr_node2.frame() == module
        assert module.locals.get("x") == [name_expr_node1.target]
        assert module.locals.get("y") == [name_expr_node2.target]
        assert "x" not in func_node.locals
        assert "y" not in class_node.locals

    @staticmethod
    def test_non_frame_node():
        """Test if the frame of non frame nodes is set correctly."""
        module = builder.parse("""
            VAR_ONE = 1

            VAR_TWO = [x for x in range(1)]
        """)
        assert module.body[0].frame() == module
        assert module.body[0].frame() == module

        assert module.body[1].value.locals["x"][0].frame() == module
        assert module.body[1].value.locals["x"][0].frame() == module
