# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Tests for the astroid builder and rebuilder module."""

import collections
import importlib
import os
import pathlib
import py_compile
import socket
import sys
import tempfile
import textwrap
import unittest
import unittest.mock

import pytest

from astroid import Instance, builder, nodes, test_utils, util
from astroid.const import IS_PYPY
from astroid.exceptions import (
    AstroidBuildingError,
    AstroidSyntaxError,
    AttributeInferenceError,
    InferenceError,
    StatementMissing,
)
from astroid.nodes.scoped_nodes import Module

from . import resources


class FromToLineNoTest(unittest.TestCase):
    def setUp(self) -> None:
        self.astroid = resources.build_file("data/format.py")

    def test_callfunc_lineno(self) -> None:
        stmts = self.astroid.body
        # on line 4:
        #    function('aeozrijz\
        #    earzer', hop)
        discard = stmts[0]
        self.assertIsInstance(discard, nodes.Expr)
        self.assertEqual(discard.fromlineno, 4)
        self.assertEqual(discard.tolineno, 5)
        callfunc = discard.value
        self.assertIsInstance(callfunc, nodes.Call)
        self.assertEqual(callfunc.fromlineno, 4)
        self.assertEqual(callfunc.tolineno, 5)
        name = callfunc.func
        self.assertIsInstance(name, nodes.Name)
        self.assertEqual(name.fromlineno, 4)
        self.assertEqual(name.tolineno, 4)
        strarg = callfunc.args[0]
        self.assertIsInstance(strarg, nodes.Const)
        if IS_PYPY:
            self.assertEqual(strarg.fromlineno, 4)
            self.assertEqual(strarg.tolineno, 5)
        else:
            self.assertEqual(strarg.fromlineno, 4)
            self.assertEqual(strarg.tolineno, 5)
        namearg = callfunc.args[1]
        self.assertIsInstance(namearg, nodes.Name)
        self.assertEqual(namearg.fromlineno, 5)
        self.assertEqual(namearg.tolineno, 5)
        # on line 10:
        #    fonction(1,
        #             2,
        #             3,
        #             4)
        discard = stmts[2]
        self.assertIsInstance(discard, nodes.Expr)
        self.assertEqual(discard.fromlineno, 10)
        self.assertEqual(discard.tolineno, 13)
        callfunc = discard.value
        self.assertIsInstance(callfunc, nodes.Call)
        self.assertEqual(callfunc.fromlineno, 10)
        self.assertEqual(callfunc.tolineno, 13)
        name = callfunc.func
        self.assertIsInstance(name, nodes.Name)
        self.assertEqual(name.fromlineno, 10)
        self.assertEqual(name.tolineno, 10)
        for i, arg in enumerate(callfunc.args):
            self.assertIsInstance(arg, nodes.Const)
            self.assertEqual(arg.fromlineno, 10 + i)
            self.assertEqual(arg.tolineno, 10 + i)

    def test_function_lineno(self) -> None:
        stmts = self.astroid.body
        # on line 15:
        #    def definition(a,
        #                   b,
        #                   c):
        #        return a + b + c
        function = stmts[3]
        self.assertIsInstance(function, nodes.FunctionDef)
        self.assertEqual(function.fromlineno, 15)
        self.assertEqual(function.tolineno, 18)
        return_ = function.body[0]
        self.assertIsInstance(return_, nodes.Return)
        self.assertEqual(return_.fromlineno, 18)
        self.assertEqual(return_.tolineno, 18)

    def test_decorated_function_lineno(self) -> None:
        astroid = builder.parse(
            """
            @decorator
            def function(
                arg):
                print (arg)
            """,
            __name__,
        )
        function = astroid["function"]
        # XXX discussable, but that's what is expected by pylint right now, similar to ClassDef
        self.assertEqual(function.fromlineno, 3)
        self.assertEqual(function.tolineno, 5)
        self.assertEqual(function.decorators.fromlineno, 2)
        self.assertEqual(function.decorators.tolineno, 2)

    @staticmethod
    def test_decorated_class_lineno() -> None:
        code = textwrap.dedent(
            """
        class A:  # L2
            ...

        @decorator
        class B:  # L6
            ...

        @deco1
        @deco2(
            var=42
        )
        class C:  # L13
            ...
        """
        )

        ast_module: nodes.Module = builder.parse(code)  # type: ignore[assignment]

        a = ast_module.body[0]
        assert isinstance(a, nodes.ClassDef)
        assert a.fromlineno == 2
        assert a.tolineno == 3

        b = ast_module.body[1]
        assert isinstance(b, nodes.ClassDef)
        assert b.fromlineno == 6
        assert b.tolineno == 7

        c = ast_module.body[2]
        assert isinstance(c, nodes.ClassDef)
        assert c.fromlineno == 13
        assert c.tolineno == 14

    @staticmethod
    def test_class_with_docstring() -> None:
        """Test class nodes which only have docstrings."""
        code = textwrap.dedent(
            '''\
        class A:
            """My docstring"""
            var = 1

        class B:
            """My docstring"""

        class C:
            """My docstring
            is long."""

        class D:
            """My docstring
            is long.
            """

        class E:
            ...
        '''
        )

        ast_module = builder.parse(code)

        a = ast_module.body[0]
        assert isinstance(a, nodes.ClassDef)
        assert a.fromlineno == 1
        assert a.tolineno == 3

        b = ast_module.body[1]
        assert isinstance(b, nodes.ClassDef)
        assert b.fromlineno == 5
        assert b.tolineno == 6

        c = ast_module.body[2]
        assert isinstance(c, nodes.ClassDef)
        assert c.fromlineno == 8
        assert c.tolineno == 10

        d = ast_module.body[3]
        assert isinstance(d, nodes.ClassDef)
        assert d.fromlineno == 12
        assert d.tolineno == 15

        e = ast_module.body[4]
        assert isinstance(d, nodes.ClassDef)
        assert e.fromlineno == 17
        assert e.tolineno == 18

    @staticmethod
    def test_function_with_docstring() -> None:
        """Test function defintions with only docstrings."""
        code = textwrap.dedent(
            '''\
        def a():
            """My docstring"""
            var = 1

        def b():
            """My docstring"""

        def c():
            """My docstring
            is long."""

        def d():
            """My docstring
            is long.
            """

        def e(a, b):
            """My docstring
            is long.
            """
        '''
        )

        ast_module = builder.parse(code)

        a = ast_module.body[0]
        assert isinstance(a, nodes.FunctionDef)
        assert a.fromlineno == 1
        assert a.tolineno == 3

        b = ast_module.body[1]
        assert isinstance(b, nodes.FunctionDef)
        assert b.fromlineno == 5
        assert b.tolineno == 6

        c = ast_module.body[2]
        assert isinstance(c, nodes.FunctionDef)
        assert c.fromlineno == 8
        assert c.tolineno == 10

        d = ast_module.body[3]
        assert isinstance(d, nodes.FunctionDef)
        assert d.fromlineno == 12
        assert d.tolineno == 15

        e = ast_module.body[4]
        assert isinstance(e, nodes.FunctionDef)
        assert e.fromlineno == 17
        assert e.tolineno == 20

    def test_class_lineno(self) -> None:
        stmts = self.astroid.body
        # on line 20:
        #    class debile(dict,
        #                 object):
        #       pass
        class_ = stmts[4]
        self.assertIsInstance(class_, nodes.ClassDef)
        self.assertEqual(class_.fromlineno, 20)
        self.assertEqual(class_.tolineno, 22)
        self.assertEqual(class_.blockstart_tolineno, 21)
        pass_ = class_.body[0]
        self.assertIsInstance(pass_, nodes.Pass)
        self.assertEqual(pass_.fromlineno, 22)
        self.assertEqual(pass_.tolineno, 22)

    def test_if_lineno(self) -> None:
        stmts = self.astroid.body
        # on line 20:
        #    if aaaa: pass
        #    else:
        #        aaaa,bbbb = 1,2
        #        aaaa,bbbb = bbbb,aaaa
        if_ = stmts[5]
        self.assertIsInstance(if_, nodes.If)
        self.assertEqual(if_.fromlineno, 24)
        self.assertEqual(if_.tolineno, 27)
        self.assertEqual(if_.blockstart_tolineno, 24)
        self.assertEqual(if_.orelse[0].fromlineno, 26)
        self.assertEqual(if_.orelse[1].tolineno, 27)

    def test_for_while_lineno(self) -> None:
        for code in (
            """
            for a in range(4):
              print (a)
              break
            else:
              print ("bouh")
            """,
            """
            while a:
              print (a)
              break
            else:
              print ("bouh")
            """,
        ):
            astroid = builder.parse(code, __name__)
            stmt = astroid.body[0]
            self.assertEqual(stmt.fromlineno, 2)
            self.assertEqual(stmt.tolineno, 6)
            self.assertEqual(stmt.blockstart_tolineno, 2)
            self.assertEqual(stmt.orelse[0].fromlineno, 6)  # XXX
            self.assertEqual(stmt.orelse[0].tolineno, 6)

    def test_try_except_lineno(self) -> None:
        astroid = builder.parse(
            """
            try:
              print (a)
            except:
              pass
            else:
              print ("bouh")
            """,
            __name__,
        )
        try_ = astroid.body[0]
        self.assertEqual(try_.fromlineno, 2)
        self.assertEqual(try_.tolineno, 7)
        self.assertEqual(try_.blockstart_tolineno, 2)
        self.assertEqual(try_.orelse[0].fromlineno, 7)  # XXX
        self.assertEqual(try_.orelse[0].tolineno, 7)
        hdlr = try_.handlers[0]
        self.assertEqual(hdlr.fromlineno, 4)
        self.assertEqual(hdlr.tolineno, 5)
        self.assertEqual(hdlr.blockstart_tolineno, 4)

    def test_try_finally_lineno(self) -> None:
        astroid = builder.parse(
            """
            try:
              print (a)
            finally:
              print ("bouh")
            """,
            __name__,
        )
        try_ = astroid.body[0]
        self.assertEqual(try_.fromlineno, 2)
        self.assertEqual(try_.tolineno, 5)
        self.assertEqual(try_.blockstart_tolineno, 2)
        self.assertEqual(try_.finalbody[0].fromlineno, 5)  # XXX
        self.assertEqual(try_.finalbody[0].tolineno, 5)

    def test_try_finally_25_lineno(self) -> None:
        astroid = builder.parse(
            """
            try:
              print (a)
            except:
              pass
            finally:
              print ("bouh")
            """,
            __name__,
        )
        try_ = astroid.body[0]
        self.assertEqual(try_.fromlineno, 2)
        self.assertEqual(try_.tolineno, 7)
        self.assertEqual(try_.blockstart_tolineno, 2)
        self.assertEqual(try_.finalbody[0].fromlineno, 7)  # XXX
        self.assertEqual(try_.finalbody[0].tolineno, 7)

    def test_with_lineno(self) -> None:
        astroid = builder.parse(
            """
            from __future__ import with_statement
            with file("/tmp/pouet") as f:
                print (f)
            """,
            __name__,
        )
        with_ = astroid.body[1]
        self.assertEqual(with_.fromlineno, 3)
        self.assertEqual(with_.tolineno, 4)
        self.assertEqual(with_.blockstart_tolineno, 3)


class BuilderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = test_utils.brainless_manager()
        self.builder = builder.AstroidBuilder(self.manager)

    def test_data_build_null_bytes(self) -> None:
        with self.assertRaises(AstroidSyntaxError):
            self.builder.string_build("\x00")

    def test_data_build_invalid_x_escape(self) -> None:
        with self.assertRaises(AstroidSyntaxError):
            self.builder.string_build('"\\x1"')

    def test_data_build_error_filename(self) -> None:
        """Check that error filename is set to modname if given."""
        with pytest.raises(AstroidSyntaxError, match="invalid escape sequence") as ctx:
            self.builder.string_build("'\\d+\\.\\d+'")
        assert isinstance(ctx.value.error, SyntaxError)
        assert ctx.value.error.filename == "<unknown>"

        with pytest.raises(AstroidSyntaxError, match="invalid escape sequence") as ctx:
            self.builder.string_build("'\\d+\\.\\d+'", modname="mymodule")
        assert isinstance(ctx.value.error, SyntaxError)
        assert ctx.value.error.filename == "mymodule"

    def test_missing_newline(self) -> None:
        """Check that a file with no trailing new line is parseable."""
        resources.build_file("data/noendingnewline.py")

    def test_missing_file(self) -> None:
        with self.assertRaises(AstroidBuildingError):
            resources.build_file("data/inexistent.py")

    def test_inspect_build0(self) -> None:
        """Test astroid tree build from a living object."""
        builtin_ast = self.manager.ast_from_module_name("builtins")
        # just check type and object are there
        builtin_ast.getattr("type")
        objectastroid = builtin_ast.getattr("object")[0]
        self.assertIsInstance(objectastroid.getattr("__new__")[0], nodes.FunctionDef)
        # check open file alias
        builtin_ast.getattr("open")
        # check 'help' is there (defined dynamically by site.py)
        builtin_ast.getattr("help")
        # check property has __init__
        pclass = builtin_ast["property"]
        self.assertIn("__init__", pclass)
        self.assertIsInstance(builtin_ast["None"], nodes.Const)
        self.assertIsInstance(builtin_ast["True"], nodes.Const)
        self.assertIsInstance(builtin_ast["False"], nodes.Const)
        self.assertIsInstance(builtin_ast["Exception"], nodes.ClassDef)
        self.assertIsInstance(builtin_ast["NotImplementedError"], nodes.ClassDef)

    def test_inspect_build1(self) -> None:
        time_ast = self.manager.ast_from_module_name("time")
        self.assertTrue(time_ast)
        self.assertEqual(time_ast["time"].args.defaults, None)

    def test_inspect_build3(self) -> None:
        self.builder.inspect_build(unittest)

    def test_inspect_build_type_object(self) -> None:
        builtin_ast = self.manager.ast_from_module_name("builtins")

        inferred = list(builtin_ast.igetattr("object"))
        self.assertEqual(len(inferred), 1)
        inferred = inferred[0]
        self.assertEqual(inferred.name, "object")
        inferred.as_string()  # no crash test

        inferred = list(builtin_ast.igetattr("type"))
        self.assertEqual(len(inferred), 1)
        inferred = inferred[0]
        self.assertEqual(inferred.name, "type")
        inferred.as_string()  # no crash test

    def test_inspect_transform_module(self) -> None:
        # ensure no cached version of the time module
        self.manager._mod_file_cache.pop(("time", None), None)
        self.manager.astroid_cache.pop("time", None)

        def transform_time(node: Module) -> None:
            if node.name == "time":
                node.transformed = True

        self.manager.register_transform(nodes.Module, transform_time)
        try:
            time_ast = self.manager.ast_from_module_name("time")
            self.assertTrue(getattr(time_ast, "transformed", False))
        finally:
            self.manager.unregister_transform(nodes.Module, transform_time)

    def test_package_name(self) -> None:
        """Test base properties and method of an astroid module."""
        datap = resources.build_file("data/__init__.py", "data")
        self.assertEqual(datap.name, "data")
        self.assertEqual(datap.package, 1)
        datap = resources.build_file("data/__init__.py", "data.__init__")
        self.assertEqual(datap.name, "data")
        self.assertEqual(datap.package, 1)
        datap = resources.build_file("data/tmp__init__.py", "data.tmp__init__")
        self.assertEqual(datap.name, "data.tmp__init__")
        self.assertEqual(datap.package, 0)

    def test_yield_parent(self) -> None:
        """Check if we added discard nodes as yield parent (w/ compiler)."""
        code = """
            def yiell(): #@
                yield 0
                if noe:
                    yield more
        """
        func = builder.extract_node(code)
        self.assertIsInstance(func, nodes.FunctionDef)
        stmt = func.body[0]
        self.assertIsInstance(stmt, nodes.Expr)
        self.assertIsInstance(stmt.value, nodes.Yield)
        self.assertIsInstance(func.body[1].body[0], nodes.Expr)
        self.assertIsInstance(func.body[1].body[0].value, nodes.Yield)

    def test_object(self) -> None:
        obj_ast = self.builder.inspect_build(object)
        self.assertIn("__setattr__", obj_ast)

    def test_newstyle_detection(self) -> None:
        data = """
            class A:
                "old style"

            class B(A):
                "old style"

            class C(object):
                "new style"

            class D(C):
                "new style"

            __metaclass__ = type

            class E(A):
                "old style"

            class F:
                "new style"
        """
        mod_ast = builder.parse(data, __name__)
        self.assertTrue(mod_ast["A"].newstyle)
        self.assertTrue(mod_ast["B"].newstyle)
        self.assertTrue(mod_ast["E"].newstyle)
        self.assertTrue(mod_ast["C"].newstyle)
        self.assertTrue(mod_ast["D"].newstyle)
        self.assertTrue(mod_ast["F"].newstyle)

    def test_globals(self) -> None:
        data = """
            CSTE = 1

            def update_global():
                global CSTE
                CSTE += 1

            def global_no_effect():
                global CSTE2
                print (CSTE)
        """
        astroid = builder.parse(data, __name__)
        self.assertEqual(len(astroid.getattr("CSTE")), 2)
        self.assertIsInstance(astroid.getattr("CSTE")[0], nodes.AssignName)
        self.assertEqual(astroid.getattr("CSTE")[0].fromlineno, 2)
        self.assertEqual(astroid.getattr("CSTE")[1].fromlineno, 6)
        with self.assertRaises(AttributeInferenceError):
            astroid.getattr("CSTE2")
        with self.assertRaises(InferenceError):
            next(astroid["global_no_effect"].ilookup("CSTE2"))

    def test_socket_build(self) -> None:
        astroid = self.builder.module_build(socket)
        # XXX just check the first one. Actually 3 objects are inferred (look at
        # the socket module) but the last one as those attributes dynamically
        # set and astroid is missing this.
        for fclass in astroid.igetattr("socket"):
            self.assertIn("connect", fclass)
            self.assertIn("send", fclass)
            self.assertIn("close", fclass)
            break

    def test_gen_expr_var_scope(self) -> None:
        data = "l = list(n for n in range(10))\n"
        astroid = builder.parse(data, __name__)
        # n unavailable outside gen expr scope
        self.assertNotIn("n", astroid)
        # test n is inferable anyway
        n = test_utils.get_name_node(astroid, "n")
        self.assertIsNot(n.scope(), astroid)
        self.assertEqual([i.__class__ for i in n.infer()], [util.Uninferable.__class__])

    def test_no_future_imports(self) -> None:
        mod = builder.parse("import sys")
        self.assertEqual(set(), mod.future_imports)

    def test_future_imports(self) -> None:
        mod = builder.parse("from __future__ import print_function")
        self.assertEqual({"print_function"}, mod.future_imports)

    def test_two_future_imports(self) -> None:
        mod = builder.parse(
            """
            from __future__ import print_function
            from __future__ import absolute_import
            """
        )
        self.assertEqual({"print_function", "absolute_import"}, mod.future_imports)

    def test_inferred_build(self) -> None:
        code = """
            class A: pass
            A.type = "class"

            def A_assign_type(self):
                print (self)
            A.assign_type = A_assign_type
            """
        astroid = builder.parse(code)
        lclass = list(astroid.igetattr("A"))
        self.assertEqual(len(lclass), 1)
        lclass = lclass[0]
        self.assertIn("assign_type", lclass.locals)
        self.assertIn("type", lclass.locals)

    def test_infer_can_assign_regular_object(self) -> None:
        mod = builder.parse(
            """
            class A:
                pass
            a = A()
            a.value = "is set"
            a.other = "is set"
        """
        )
        obj = list(mod.igetattr("a"))
        self.assertEqual(len(obj), 1)
        obj = obj[0]
        self.assertIsInstance(obj, Instance)
        self.assertIn("value", obj.instance_attrs)
        self.assertIn("other", obj.instance_attrs)

    def test_infer_can_assign_has_slots(self) -> None:
        mod = builder.parse(
            """
            class A:
                __slots__ = ('value',)
            a = A()
            a.value = "is set"
            a.other = "not set"
        """
        )
        obj = list(mod.igetattr("a"))
        self.assertEqual(len(obj), 1)
        obj = obj[0]
        self.assertIsInstance(obj, Instance)
        self.assertIn("value", obj.instance_attrs)
        self.assertNotIn("other", obj.instance_attrs)

    def test_infer_can_assign_no_classdict(self) -> None:
        mod = builder.parse(
            """
            a = object()
            a.value = "not set"
        """
        )
        obj = list(mod.igetattr("a"))
        self.assertEqual(len(obj), 1)
        obj = obj[0]
        self.assertIsInstance(obj, Instance)
        self.assertNotIn("value", obj.instance_attrs)

    def test_augassign_attr(self) -> None:
        builder.parse(
            """
            class Counter:
                v = 0
                def inc(self):
                    self.v += 1
            """,
            __name__,
        )
        # TODO: Check self.v += 1 generate AugAssign(AssAttr(...)),
        # not AugAssign(GetAttr(AssName...))

    def test_inferred_dont_pollute(self) -> None:
        code = """
            def func(a=None):
                a.custom_attr = 0
            def func2(a={}):
                a.custom_attr = 0
            """
        builder.parse(code)
        # pylint: disable=no-member
        nonetype = nodes.const_factory(None)
        self.assertNotIn("custom_attr", nonetype.locals)
        self.assertNotIn("custom_attr", nonetype.instance_attrs)
        nonetype = nodes.const_factory({})
        self.assertNotIn("custom_attr", nonetype.locals)
        self.assertNotIn("custom_attr", nonetype.instance_attrs)

    def test_asstuple(self) -> None:
        code = "a, b = range(2)"
        astroid = builder.parse(code)
        self.assertIn("b", astroid.locals)
        code = """
            def visit_if(self, node):
                node.test, body = node.tests[0]
            """
        astroid = builder.parse(code)
        self.assertIn("body", astroid["visit_if"].locals)

    def test_build_constants(self) -> None:
        """Test expected values of constants after rebuilding."""
        code = """
            def func():
                return None
                return
                return 'None'
            """
        astroid = builder.parse(code)
        none, nothing, chain = (ret.value for ret in astroid.body[0].body)
        self.assertIsInstance(none, nodes.Const)
        self.assertIsNone(none.value)
        self.assertIsNone(nothing)
        self.assertIsInstance(chain, nodes.Const)
        self.assertEqual(chain.value, "None")

    def test_not_implemented(self) -> None:
        node = builder.extract_node(
            """
        NotImplemented #@
        """
        )
        inferred = next(node.infer())
        self.assertIsInstance(inferred, nodes.Const)
        self.assertEqual(inferred.value, NotImplemented)

    def test_type_comments_without_content(self) -> None:
        node = builder.parse(
            """
            a = 1 # type: # any comment
        """
        )
        assert node


class FileBuildTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = resources.build_file("data/module.py", "data.module")

    def test_module_base_props(self) -> None:
        """Test base properties and method of an astroid module."""
        module = self.module
        self.assertEqual(module.name, "data.module")
        assert isinstance(module.doc_node, nodes.Const)
        self.assertEqual(module.doc_node.value, "test module for astroid\n")
        self.assertEqual(module.fromlineno, 0)
        self.assertIsNone(module.parent)
        self.assertEqual(module.frame(), module)
        self.assertEqual(module.frame(), module)
        self.assertEqual(module.root(), module)
        self.assertEqual(module.file, os.path.abspath(resources.find("data/module.py")))
        self.assertEqual(module.pure_python, 1)
        self.assertEqual(module.package, 0)
        self.assertFalse(module.is_statement)
        with self.assertRaises(StatementMissing):
            with pytest.warns(DeprecationWarning) as records:
                self.assertEqual(module.statement(future=True), module)
        assert len(records) == 1
        with self.assertRaises(StatementMissing):
            module.statement()

    def test_module_locals(self) -> None:
        """Test the 'locals' dictionary of an astroid module."""
        module = self.module
        _locals = module.locals
        self.assertIs(_locals, module.globals)
        keys = sorted(_locals.keys())
        should = [
            "MY_DICT",
            "NameNode",
            "YO",
            "YOUPI",
            "__revision__",
            "global_access",
            "modutils",
            "four_args",
            "os",
            "redirect",
        ]
        should.sort()
        self.assertEqual(keys, sorted(should))

    def test_function_base_props(self) -> None:
        """Test base properties and method of an astroid function."""
        module = self.module
        function = module["global_access"]
        self.assertEqual(function.name, "global_access")
        assert isinstance(function.doc_node, nodes.Const)
        self.assertEqual(function.doc_node.value, "function test")
        self.assertEqual(function.fromlineno, 11)
        self.assertTrue(function.parent)
        self.assertEqual(function.frame(), function)
        self.assertEqual(function.parent.frame(), module)
        self.assertEqual(function.frame(), function)
        self.assertEqual(function.parent.frame(), module)
        self.assertEqual(function.root(), module)
        self.assertEqual([n.name for n in function.args.args], ["key", "val"])
        self.assertEqual(function.type, "function")

    def test_function_locals(self) -> None:
        """Test the 'locals' dictionary of an astroid function."""
        _locals = self.module["global_access"].locals
        self.assertEqual(len(_locals), 4)
        keys = sorted(_locals.keys())
        self.assertEqual(keys, ["i", "key", "local", "val"])

    def test_class_base_props(self) -> None:
        """Test base properties and method of an astroid class."""
        module = self.module
        klass = module["YO"]
        self.assertEqual(klass.name, "YO")
        assert isinstance(klass.doc_node, nodes.Const)
        self.assertEqual(klass.doc_node.value, "hehe\n    haha")
        self.assertEqual(klass.fromlineno, 25)
        self.assertTrue(klass.parent)
        self.assertEqual(klass.frame(), klass)
        self.assertEqual(klass.parent.frame(), module)
        self.assertEqual(klass.frame(), klass)
        self.assertEqual(klass.parent.frame(), module)
        self.assertEqual(klass.root(), module)
        self.assertEqual(klass.basenames, [])
        self.assertTrue(klass.newstyle)

    def test_class_locals(self) -> None:
        """Test the 'locals' dictionary of an astroid class."""
        module = self.module
        klass1 = module["YO"]
        locals1 = klass1.locals
        keys = sorted(locals1.keys())
        assert_keys = ["__annotations__", "__init__", "__module__", "__qualname__", "a"]
        self.assertEqual(keys, assert_keys)
        klass2 = module["YOUPI"]
        locals2 = klass2.locals
        keys = locals2.keys()
        assert_keys = [
            "__annotations__",
            "__init__",
            "__module__",
            "__qualname__",
            "class_attr",
            "class_method",
            "method",
            "static_method",
        ]
        self.assertEqual(sorted(keys), assert_keys)

    def test_class_instance_attrs(self) -> None:
        module = self.module
        klass1 = module["YO"]
        klass2 = module["YOUPI"]
        self.assertEqual(list(klass1.instance_attrs.keys()), ["yo"])
        self.assertEqual(list(klass2.instance_attrs.keys()), ["member"])

    def test_class_basenames(self) -> None:
        module = self.module
        klass1 = module["YO"]
        klass2 = module["YOUPI"]
        self.assertEqual(klass1.basenames, [])
        self.assertEqual(klass2.basenames, ["YO"])

    def test_method_base_props(self) -> None:
        """Test base properties and method of an astroid method."""
        klass2 = self.module["YOUPI"]
        # "normal" method
        method = klass2["method"]
        self.assertEqual(method.name, "method")
        self.assertEqual([n.name for n in method.args.args], ["self"])
        assert isinstance(method.doc_node, nodes.Const)
        self.assertEqual(method.doc_node.value, "method\n        test")
        self.assertEqual(method.fromlineno, 48)
        self.assertEqual(method.type, "method")
        # class method
        method = klass2["class_method"]
        self.assertEqual([n.name for n in method.args.args], ["cls"])
        self.assertEqual(method.type, "classmethod")
        # static method
        method = klass2["static_method"]
        self.assertEqual(method.args.args, [])
        self.assertEqual(method.type, "staticmethod")

    def test_method_locals(self) -> None:
        """Test the 'locals' dictionary of an astroid method."""
        method = self.module["YOUPI"]["method"]
        _locals = method.locals
        keys = sorted(_locals)
        # ListComp variables are not accessible outside
        self.assertEqual(len(_locals), 3)
        self.assertEqual(keys, ["autre", "local", "self"])

    def test_unknown_encoding(self) -> None:
        with self.assertRaises(AstroidSyntaxError):
            resources.build_file("data/invalid_encoding.py")


def test_module_build_dunder_file() -> None:
    """Test that module_build() can work with modules that have the *__file__*
    attribute.
    """
    module = builder.AstroidBuilder().module_build(collections)
    assert module.path[0] == collections.__file__


def test_parse_module_with_invalid_type_comments_does_not_crash():
    node = builder.parse(
        """
    # op {
    #   name: "AssignAddVariableOp"
    #   input_arg {
    #     name: "resource"
    #     type: DT_RESOURCE
    #   }
    #   input_arg {
    #     name: "value"
    #     type_attr: "dtype"
    #   }
    #   attr {
    #     name: "dtype"
    #     type: "type"
    #   }
    #   is_stateful: true
    # }
    a, b = 2
    """
    )
    assert isinstance(node, nodes.Module)


def test_arguments_of_signature() -> None:
    """Test that arguments is None for function without an inferable signature."""
    node = builder.extract_node("int")
    classdef: nodes.ClassDef = next(node.infer())
    assert all(i.args.args is None for i in classdef.getattr("__dir__"))


class HermeticInterpreterTest(unittest.TestCase):
    """Modeled on https://github.com/pylint-dev/astroid/pull/1207#issuecomment-951455588."""

    @classmethod
    def setUpClass(cls):
        """Simulate a hermetic interpreter environment having no code on the filesystem."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            sys.path.append(tmp_dir)

            # Write a python file and compile it to .pyc
            # To make this test have even more value, we would need to come up with some
            # code that gets inferred differently when we get its "partial representation".
            # This code is too simple for that. But we can't use builtins either, because we would
            # have to delete builtins from the filesystem.  But even if we engineered that,
            # the difference might evaporate over time as inference changes.
            cls.code_snippet = "def func():  return 42"
            with tempfile.NamedTemporaryFile(
                mode="w", dir=tmp_dir, suffix=".py", delete=False
            ) as tmp:
                tmp.write(cls.code_snippet)
                pyc_file = py_compile.compile(tmp.name)
                cls.pyc_name = tmp.name.replace(".py", ".pyc")
            os.remove(tmp.name)
            os.rename(pyc_file, cls.pyc_name)

            # Import the module
            cls.imported_module_path = pathlib.Path(cls.pyc_name)
            cls.imported_module = importlib.import_module(cls.imported_module_path.stem)

            # Delete source code from module object, filesystem, and path
            del cls.imported_module.__file__
            os.remove(cls.imported_module_path)
            sys.path.remove(tmp_dir)

    def test_build_from_live_module_without_source_file(self) -> None:
        """Assert that inspect_build() is not called.

        See comment in module_build() before the call to inspect_build():
            "get a partial representation by introspection"

        This "partial representation" was presumably causing unexpected behavior.
        """
        # Sanity check
        self.assertIsNone(
            self.imported_module.__loader__.get_source(self.imported_module_path.stem)
        )
        with self.assertRaises(AttributeError):
            _ = self.imported_module.__file__

        my_builder = builder.AstroidBuilder()
        with unittest.mock.patch.object(
            self.imported_module.__loader__,
            "get_source",
            return_value=self.code_snippet,
        ):
            with unittest.mock.patch.object(
                my_builder, "inspect_build", side_effect=AssertionError
            ):
                my_builder.module_build(
                    self.imported_module, modname=self.imported_module_path.stem
                )
