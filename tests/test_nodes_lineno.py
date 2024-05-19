# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import textwrap

import pytest

import astroid
from astroid import builder, nodes
from astroid.const import PY310_PLUS, PY312_PLUS


class TestLinenoColOffset:
    """Test 'lineno', 'col_offset', 'end_lineno', and 'end_col_offset' for all
    nodes.
    """

    @staticmethod
    def test_end_lineno_container() -> None:
        """Container nodes: List, Tuple, Set."""
        code = textwrap.dedent(
            """
        [1, 2, 3]  #@
        [  #@
            1, 2, 3
        ]
        (1, 2, 3)  #@
        {1, 2, 3}  #@
        """
        ).strip()
        ast_nodes = builder.extract_node(code)
        assert isinstance(ast_nodes, list) and len(ast_nodes) == 4

        c1 = ast_nodes[0]
        assert isinstance(c1, nodes.List)
        assert (c1.lineno, c1.col_offset) == (1, 0)
        assert (c1.end_lineno, c1.end_col_offset) == (1, 9)

        c2 = ast_nodes[1]
        assert isinstance(c2, nodes.List)
        assert (c2.lineno, c2.col_offset) == (2, 0)
        assert (c2.end_lineno, c2.end_col_offset) == (4, 1)

        c3 = ast_nodes[2]
        assert isinstance(c3, nodes.Tuple)
        assert (c3.lineno, c3.col_offset) == (5, 0)
        assert (c3.end_lineno, c3.end_col_offset) == (5, 9)

        c4 = ast_nodes[3]
        assert isinstance(c4, nodes.Set)
        assert (c4.lineno, c4.col_offset) == (6, 0)
        assert (c4.end_lineno, c4.end_col_offset) == (6, 9)

    @staticmethod
    def test_end_lineno_name() -> None:
        """Name, Assign, AssignName, Delete, DelName."""
        code = textwrap.dedent(
            """
        var = 42  #@
        var  #@
        del var  #@

        var2 = (  #@
            1, 2, 3
        )
        """
        ).strip()
        ast_nodes = builder.extract_node(code)
        assert isinstance(ast_nodes, list) and len(ast_nodes) == 4

        n1 = ast_nodes[0]
        assert isinstance(n1, nodes.Assign)
        assert isinstance(n1.targets[0], nodes.AssignName)
        assert isinstance(n1.value, nodes.Const)
        assert (n1.lineno, n1.col_offset) == (1, 0)
        assert (n1.end_lineno, n1.end_col_offset) == (1, 8)
        assert (n1.targets[0].lineno, n1.targets[0].col_offset) == (1, 0)
        assert (n1.targets[0].end_lineno, n1.targets[0].end_col_offset) == (1, 3)
        assert (n1.value.lineno, n1.value.col_offset) == (1, 6)
        assert (n1.value.end_lineno, n1.value.end_col_offset) == (1, 8)

        n2 = ast_nodes[1]
        assert isinstance(n2, nodes.Name)
        assert (n2.lineno, n2.col_offset) == (2, 0)
        assert (n2.end_lineno, n2.end_col_offset) == (2, 3)

        n3 = ast_nodes[2]
        assert isinstance(n3, nodes.Delete) and isinstance(n3.targets[0], nodes.DelName)
        assert (n3.lineno, n3.col_offset) == (3, 0)
        assert (n3.end_lineno, n3.end_col_offset) == (3, 7)
        assert (n3.targets[0].lineno, n3.targets[0].col_offset) == (3, 4)
        assert (n3.targets[0].end_lineno, n3.targets[0].end_col_offset) == (3, 7)

        n4 = ast_nodes[3]
        assert isinstance(n4, nodes.Assign)
        assert isinstance(n4.targets[0], nodes.AssignName)
        assert (n4.lineno, n4.col_offset) == (5, 0)
        assert (n4.end_lineno, n4.end_col_offset) == (7, 1)
        assert (n4.targets[0].lineno, n4.targets[0].col_offset) == (5, 0)
        assert (n4.targets[0].end_lineno, n4.targets[0].end_col_offset) == (5, 4)

    @staticmethod
    def test_end_lineno_attribute() -> None:
        """Attribute, AssignAttr, DelAttr."""
        code = textwrap.dedent(
            """
        class X:
            var = 42

        X.var2 = 2  #@
        X.var2  #@
        del X.var2  #@
        """
        ).strip()
        ast_nodes = builder.extract_node(code)
        assert isinstance(ast_nodes, list) and len(ast_nodes) == 3

        a1 = ast_nodes[0]
        assert isinstance(a1, nodes.Assign)
        assert isinstance(a1.targets[0], nodes.AssignAttr)
        assert isinstance(a1.value, nodes.Const)
        assert (a1.lineno, a1.col_offset) == (4, 0)
        assert (a1.end_lineno, a1.end_col_offset) == (4, 10)
        assert (a1.targets[0].lineno, a1.targets[0].col_offset) == (4, 0)
        assert (a1.targets[0].end_lineno, a1.targets[0].end_col_offset) == (4, 6)
        assert (a1.value.lineno, a1.value.col_offset) == (4, 9)
        assert (a1.value.end_lineno, a1.value.end_col_offset) == (4, 10)

        a2 = ast_nodes[1]
        assert isinstance(a2, nodes.Attribute) and isinstance(a2.expr, nodes.Name)
        assert (a2.lineno, a2.col_offset) == (5, 0)
        assert (a2.end_lineno, a2.end_col_offset) == (5, 6)
        assert (a2.expr.lineno, a2.expr.col_offset) == (5, 0)
        assert (a2.expr.end_lineno, a2.expr.end_col_offset) == (5, 1)

        a3 = ast_nodes[2]
        assert isinstance(a3, nodes.Delete) and isinstance(a3.targets[0], nodes.DelAttr)
        assert (a3.lineno, a3.col_offset) == (6, 0)
        assert (a3.end_lineno, a3.end_col_offset) == (6, 10)
        assert (a3.targets[0].lineno, a3.targets[0].col_offset) == (6, 4)
        assert (a3.targets[0].end_lineno, a3.targets[0].end_col_offset) == (6, 10)

    @staticmethod
    def test_end_lineno_call() -> None:
        """Call, Keyword."""
        code = textwrap.dedent(
            """
        func(arg1, arg2=value)  #@
        """
        ).strip()
        c1 = builder.extract_node(code)
        assert isinstance(c1, nodes.Call)
        assert isinstance(c1.func, nodes.Name)
        assert isinstance(c1.args[0], nodes.Name)
        assert isinstance(c1.keywords[0], nodes.Keyword)
        assert isinstance(c1.keywords[0].value, nodes.Name)

        assert (c1.lineno, c1.col_offset) == (1, 0)
        assert (c1.end_lineno, c1.end_col_offset) == (1, 22)
        assert (c1.func.lineno, c1.func.col_offset) == (1, 0)
        assert (c1.func.end_lineno, c1.func.end_col_offset) == (1, 4)

        assert (c1.args[0].lineno, c1.args[0].col_offset) == (1, 5)
        assert (c1.args[0].end_lineno, c1.args[0].end_col_offset) == (1, 9)

        # fmt: off
        assert (c1.keywords[0].lineno, c1.keywords[0].col_offset) == (1, 11)
        assert (c1.keywords[0].end_lineno, c1.keywords[0].end_col_offset) == (1, 21)
        assert (c1.keywords[0].value.lineno, c1.keywords[0].value.col_offset) == (1, 16)
        assert (c1.keywords[0].value.end_lineno, c1.keywords[0].value.end_col_offset) == (1, 21)
        # fmt: on

    @staticmethod
    def test_end_lineno_assignment() -> None:
        """Assign, AnnAssign, AugAssign."""
        code = textwrap.dedent(
            """
        var = 2  #@
        var2: int = 2  #@
        var3 += 2  #@
        """
        ).strip()
        ast_nodes = builder.extract_node(code)
        assert isinstance(ast_nodes, list) and len(ast_nodes) == 3

        a1 = ast_nodes[0]
        assert isinstance(a1, nodes.Assign)
        assert isinstance(a1.targets[0], nodes.AssignName)
        assert isinstance(a1.value, nodes.Const)
        assert (a1.lineno, a1.col_offset) == (1, 0)
        assert (a1.end_lineno, a1.end_col_offset) == (1, 7)
        assert (a1.targets[0].lineno, a1.targets[0].col_offset) == (1, 0)
        assert (a1.targets[0].end_lineno, a1.targets[0].end_col_offset) == (1, 3)
        assert (a1.value.lineno, a1.value.col_offset) == (1, 6)
        assert (a1.value.end_lineno, a1.value.end_col_offset) == (1, 7)

        a2 = ast_nodes[1]
        assert isinstance(a2, nodes.AnnAssign)
        assert isinstance(a2.target, nodes.AssignName)
        assert isinstance(a2.annotation, nodes.Name)
        assert isinstance(a2.value, nodes.Const)
        assert (a2.lineno, a2.col_offset) == (2, 0)
        assert (a2.end_lineno, a2.end_col_offset) == (2, 13)
        assert (a2.target.lineno, a2.target.col_offset) == (2, 0)
        assert (a2.target.end_lineno, a2.target.end_col_offset) == (2, 4)
        assert (a2.annotation.lineno, a2.annotation.col_offset) == (2, 6)
        assert (a2.annotation.end_lineno, a2.annotation.end_col_offset) == (2, 9)
        assert (a2.value.lineno, a2.value.col_offset) == (2, 12)
        assert (a2.value.end_lineno, a2.value.end_col_offset) == (2, 13)

        a3 = ast_nodes[2]
        assert isinstance(a3, nodes.AugAssign)
        assert isinstance(a3.target, nodes.AssignName)
        assert isinstance(a3.value, nodes.Const)
        assert (a3.lineno, a3.col_offset) == (3, 0)
        assert (a3.end_lineno, a3.end_col_offset) == (3, 9)
        assert (a3.target.lineno, a3.target.col_offset) == (3, 0)
        assert (a3.target.end_lineno, a3.target.end_col_offset) == (3, 4)
        assert (a3.value.lineno, a3.value.col_offset) == (3, 8)
        assert (a3.value.end_lineno, a3.value.end_col_offset) == (3, 9)

    @staticmethod
    def test_end_lineno_mix_stmts() -> None:
        """Assert, Break, Continue, Global, Nonlocal, Pass, Raise, Return, Expr."""
        code = textwrap.dedent(
            """
        assert True, "Some message"  #@
        break  #@
        continue  #@
        global var  #@
        nonlocal var  #@
        pass  #@
        raise Exception from ex  #@
        return 42  #@
        var  #@
        """
        ).strip()
        ast_nodes = builder.extract_node(code)
        assert isinstance(ast_nodes, list) and len(ast_nodes) == 9

        s1 = ast_nodes[0]
        assert isinstance(s1, nodes.Assert)
        assert isinstance(s1.test, nodes.Const)
        assert isinstance(s1.fail, nodes.Const)
        assert (s1.lineno, s1.col_offset) == (1, 0)
        assert (s1.end_lineno, s1.end_col_offset) == (1, 27)
        assert (s1.test.lineno, s1.test.col_offset) == (1, 7)
        assert (s1.test.end_lineno, s1.test.end_col_offset) == (1, 11)
        assert (s1.fail.lineno, s1.fail.col_offset) == (1, 13)
        assert (s1.fail.end_lineno, s1.fail.end_col_offset) == (1, 27)

        s2 = ast_nodes[1]
        assert isinstance(s2, nodes.Break)
        assert (s2.lineno, s2.col_offset) == (2, 0)
        assert (s2.end_lineno, s2.end_col_offset) == (2, 5)

        s3 = ast_nodes[2]
        assert isinstance(s3, nodes.Continue)
        assert (s3.lineno, s3.col_offset) == (3, 0)
        assert (s3.end_lineno, s3.end_col_offset) == (3, 8)

        s4 = ast_nodes[3]
        assert isinstance(s4, nodes.Global)
        assert (s4.lineno, s4.col_offset) == (4, 0)
        assert (s4.end_lineno, s4.end_col_offset) == (4, 10)

        s5 = ast_nodes[4]
        assert isinstance(s5, nodes.Nonlocal)
        assert (s5.lineno, s5.col_offset) == (5, 0)
        assert (s5.end_lineno, s5.end_col_offset) == (5, 12)

        s6 = ast_nodes[5]
        assert isinstance(s6, nodes.Pass)
        assert (s6.lineno, s6.col_offset) == (6, 0)
        assert (s6.end_lineno, s6.end_col_offset) == (6, 4)

        s7 = ast_nodes[6]
        assert isinstance(s7, nodes.Raise)
        assert isinstance(s7.exc, nodes.Name)
        assert isinstance(s7.cause, nodes.Name)
        assert (s7.lineno, s7.col_offset) == (7, 0)
        assert (s7.end_lineno, s7.end_col_offset) == (7, 23)
        assert (s7.exc.lineno, s7.exc.col_offset) == (7, 6)
        assert (s7.exc.end_lineno, s7.exc.end_col_offset) == (7, 15)
        assert (s7.cause.lineno, s7.cause.col_offset) == (7, 21)
        assert (s7.cause.end_lineno, s7.cause.end_col_offset) == (7, 23)

        s8 = ast_nodes[7]
        assert isinstance(s8, nodes.Return)
        assert isinstance(s8.value, nodes.Const)
        assert (s8.lineno, s8.col_offset) == (8, 0)
        assert (s8.end_lineno, s8.end_col_offset) == (8, 9)
        assert (s8.value.lineno, s8.value.col_offset) == (8, 7)
        assert (s8.value.end_lineno, s8.value.end_col_offset) == (8, 9)

        s9 = ast_nodes[8].parent
        assert isinstance(s9, nodes.Expr)
        assert isinstance(s9.value, nodes.Name)
        assert (s9.lineno, s9.col_offset) == (9, 0)
        assert (s9.end_lineno, s9.end_col_offset) == (9, 3)
        assert (s9.value.lineno, s9.value.col_offset) == (9, 0)
        assert (s9.value.end_lineno, s9.value.end_col_offset) == (9, 3)

    @staticmethod
    def test_end_lineno_mix_nodes() -> None:
        """Await, Starred, Yield, YieldFrom."""
        code = textwrap.dedent(
            """
        await func  #@
        *args  #@
        yield 42  #@
        yield from (1, 2)  #@
        """
        ).strip()
        ast_nodes = builder.extract_node(code)
        assert isinstance(ast_nodes, list) and len(ast_nodes) == 4

        n1 = ast_nodes[0]
        assert isinstance(n1, nodes.Await)
        assert isinstance(n1.value, nodes.Name)
        assert (n1.lineno, n1.col_offset) == (1, 0)
        assert (n1.end_lineno, n1.end_col_offset) == (1, 10)
        assert (n1.value.lineno, n1.value.col_offset) == (1, 6)
        assert (n1.value.end_lineno, n1.value.end_col_offset) == (1, 10)

        n2 = ast_nodes[1]
        assert isinstance(n2, nodes.Starred)
        assert isinstance(n2.value, nodes.Name)
        assert (n2.lineno, n2.col_offset) == (2, 0)
        assert (n2.end_lineno, n2.end_col_offset) == (2, 5)
        assert (n2.value.lineno, n2.value.col_offset) == (2, 1)
        assert (n2.value.end_lineno, n2.value.end_col_offset) == (2, 5)

        n3 = ast_nodes[2]
        assert isinstance(n3, nodes.Yield)
        assert isinstance(n3.value, nodes.Const)
        assert (n3.lineno, n3.col_offset) == (3, 0)
        assert (n3.end_lineno, n3.end_col_offset) == (3, 8)
        assert (n3.value.lineno, n3.value.col_offset) == (3, 6)
        assert (n3.value.end_lineno, n3.value.end_col_offset) == (3, 8)

        n4 = ast_nodes[3]
        assert isinstance(n4, nodes.YieldFrom)
        assert isinstance(n4.value, nodes.Tuple)
        assert (n4.lineno, n4.col_offset) == (4, 0)
        assert (n4.end_lineno, n4.end_col_offset) == (4, 17)
        assert (n4.value.lineno, n4.value.col_offset) == (4, 11)
        assert (n4.value.end_lineno, n4.value.end_col_offset) == (4, 17)

    @staticmethod
    def test_end_lineno_ops() -> None:
        """BinOp, BoolOp, UnaryOp, Compare."""
        code = textwrap.dedent(
            """
        x + y  #@
        a and b  #@
        -var  #@
        a < b  #@
        """
        ).strip()
        ast_nodes = builder.extract_node(code)
        assert isinstance(ast_nodes, list) and len(ast_nodes) == 4

        o1 = ast_nodes[0]
        assert isinstance(o1, nodes.BinOp)
        assert isinstance(o1.left, nodes.Name)
        assert isinstance(o1.right, nodes.Name)
        assert (o1.lineno, o1.col_offset) == (1, 0)
        assert (o1.end_lineno, o1.end_col_offset) == (1, 5)
        assert (o1.left.lineno, o1.left.col_offset) == (1, 0)
        assert (o1.left.end_lineno, o1.left.end_col_offset) == (1, 1)
        assert (o1.right.lineno, o1.right.col_offset) == (1, 4)
        assert (o1.right.end_lineno, o1.right.end_col_offset) == (1, 5)

        o2 = ast_nodes[1]
        assert isinstance(o2, nodes.BoolOp)
        assert isinstance(o2.values[0], nodes.Name)
        assert isinstance(o2.values[1], nodes.Name)
        assert (o2.lineno, o2.col_offset) == (2, 0)
        assert (o2.end_lineno, o2.end_col_offset) == (2, 7)
        assert (o2.values[0].lineno, o2.values[0].col_offset) == (2, 0)
        assert (o2.values[0].end_lineno, o2.values[0].end_col_offset) == (2, 1)
        assert (o2.values[1].lineno, o2.values[1].col_offset) == (2, 6)
        assert (o2.values[1].end_lineno, o2.values[1].end_col_offset) == (2, 7)

        o3 = ast_nodes[2]
        assert isinstance(o3, nodes.UnaryOp)
        assert isinstance(o3.operand, nodes.Name)
        assert (o3.lineno, o3.col_offset) == (3, 0)
        assert (o3.end_lineno, o3.end_col_offset) == (3, 4)
        assert (o3.operand.lineno, o3.operand.col_offset) == (3, 1)
        assert (o3.operand.end_lineno, o3.operand.end_col_offset) == (3, 4)

        o4 = ast_nodes[3]
        assert isinstance(o4, nodes.Compare)
        assert isinstance(o4.left, nodes.Name)
        assert isinstance(o4.ops[0][1], nodes.Name)
        assert (o4.lineno, o4.col_offset) == (4, 0)
        assert (o4.end_lineno, o4.end_col_offset) == (4, 5)
        assert (o4.left.lineno, o4.left.col_offset) == (4, 0)
        assert (o4.left.end_lineno, o4.left.end_col_offset) == (4, 1)
        assert (o4.ops[0][1].lineno, o4.ops[0][1].col_offset) == (4, 4)
        assert (o4.ops[0][1].end_lineno, o4.ops[0][1].end_col_offset) == (4, 5)

    @staticmethod
    def test_end_lineno_if() -> None:
        """If, IfExp, NamedExpr."""
        code = textwrap.dedent(
            """
        if (  #@
            var := 2  #@
        ):
            pass
        else:
            pass

        2 if True else 1  #@
        """
        ).strip()
        ast_nodes = builder.extract_node(code)
        assert isinstance(ast_nodes, list) and len(ast_nodes) == 3

        i1 = ast_nodes[0]
        assert isinstance(i1, nodes.If)
        assert isinstance(i1.test, nodes.NamedExpr)
        assert isinstance(i1.body[0], nodes.Pass)
        assert isinstance(i1.orelse[0], nodes.Pass)
        assert (i1.lineno, i1.col_offset) == (1, 0)
        assert (i1.end_lineno, i1.end_col_offset) == (6, 8)
        assert (i1.test.lineno, i1.test.col_offset) == (2, 4)
        assert (i1.test.end_lineno, i1.test.end_col_offset) == (2, 12)
        assert (i1.body[0].lineno, i1.body[0].col_offset) == (4, 4)
        assert (i1.body[0].end_lineno, i1.body[0].end_col_offset) == (4, 8)
        assert (i1.orelse[0].lineno, i1.orelse[0].col_offset) == (6, 4)
        assert (i1.orelse[0].end_lineno, i1.orelse[0].end_col_offset) == (6, 8)

        i2 = ast_nodes[1]
        assert isinstance(i2, nodes.NamedExpr)
        assert isinstance(i2.target, nodes.AssignName)
        assert isinstance(i2.value, nodes.Const)
        assert (i2.lineno, i2.col_offset) == (2, 4)
        assert (i2.end_lineno, i2.end_col_offset) == (2, 12)
        assert (i2.target.lineno, i2.target.col_offset) == (2, 4)
        assert (i2.target.end_lineno, i2.target.end_col_offset) == (2, 7)
        assert (i2.value.lineno, i2.value.col_offset) == (2, 11)
        assert (i2.value.end_lineno, i2.value.end_col_offset) == (2, 12)

        i3 = ast_nodes[2]
        assert isinstance(i3, nodes.IfExp)
        assert isinstance(i3.test, nodes.Const)
        assert isinstance(i3.body, nodes.Const)
        assert isinstance(i3.orelse, nodes.Const)
        assert (i3.lineno, i3.col_offset) == (8, 0)
        assert (i3.end_lineno, i3.end_col_offset) == (8, 16)
        assert (i3.test.lineno, i3.test.col_offset) == (8, 5)
        assert (i3.test.end_lineno, i3.test.end_col_offset) == (8, 9)
        assert (i3.body.lineno, i3.body.col_offset) == (8, 0)
        assert (i3.body.end_lineno, i3.body.end_col_offset) == (8, 1)
        assert (i3.orelse.lineno, i3.orelse.col_offset) == (8, 15)
        assert (i3.orelse.end_lineno, i3.orelse.end_col_offset) == (8, 16)

    @staticmethod
    def test_end_lineno_for() -> None:
        """For, AsyncFor."""
        code = textwrap.dedent(
            """
        for i in lst:  #@
            pass
        else:
            pass

        async for i in lst:  #@
            pass
        """
        ).strip()
        ast_nodes = builder.extract_node(code)
        assert isinstance(ast_nodes, list) and len(ast_nodes) == 2

        f1 = ast_nodes[0]
        assert isinstance(f1, nodes.For)
        assert isinstance(f1.target, nodes.AssignName)
        assert isinstance(f1.iter, nodes.Name)
        assert isinstance(f1.body[0], nodes.Pass)
        assert isinstance(f1.orelse[0], nodes.Pass)
        assert (f1.lineno, f1.col_offset) == (1, 0)
        assert (f1.end_lineno, f1.end_col_offset) == (4, 8)
        assert (f1.target.lineno, f1.target.col_offset) == (1, 4)
        assert (f1.target.end_lineno, f1.target.end_col_offset) == (1, 5)
        assert (f1.iter.lineno, f1.iter.col_offset) == (1, 9)
        assert (f1.iter.end_lineno, f1.iter.end_col_offset) == (1, 12)
        assert (f1.body[0].lineno, f1.body[0].col_offset) == (2, 4)
        assert (f1.body[0].end_lineno, f1.body[0].end_col_offset) == (2, 8)
        assert (f1.orelse[0].lineno, f1.orelse[0].col_offset) == (4, 4)
        assert (f1.orelse[0].end_lineno, f1.orelse[0].end_col_offset) == (4, 8)

        f2 = ast_nodes[1]
        assert isinstance(f2, nodes.AsyncFor)
        assert isinstance(f2.target, nodes.AssignName)
        assert isinstance(f2.iter, nodes.Name)
        assert isinstance(f2.body[0], nodes.Pass)
        assert (f2.lineno, f2.col_offset) == (6, 0)
        assert (f2.end_lineno, f2.end_col_offset) == (7, 8)
        assert (f2.target.lineno, f2.target.col_offset) == (6, 10)
        assert (f2.target.end_lineno, f2.target.end_col_offset) == (6, 11)
        assert (f2.iter.lineno, f2.iter.col_offset) == (6, 15)
        assert (f2.iter.end_lineno, f2.iter.end_col_offset) == (6, 18)
        assert (f2.body[0].lineno, f2.body[0].col_offset) == (7, 4)
        assert (f2.body[0].end_lineno, f2.body[0].end_col_offset) == (7, 8)

    @staticmethod
    def test_end_lineno_const() -> None:
        """Const (int, str, bool, None, bytes, ellipsis)."""
        code = textwrap.dedent(
            """
        2  #@
        "Hello"  #@
        True  #@
        None  #@
        b"01"  #@
        ...  #@
        """
        ).strip()
        ast_nodes = builder.extract_node(code)
        assert isinstance(ast_nodes, list) and len(ast_nodes) == 6

        c1 = ast_nodes[0]
        assert isinstance(c1, nodes.Const)
        assert (c1.lineno, c1.col_offset) == (1, 0)
        assert (c1.end_lineno, c1.end_col_offset) == (1, 1)

        c2 = ast_nodes[1]
        assert isinstance(c2, nodes.Const)
        assert (c2.lineno, c2.col_offset) == (2, 0)
        assert (c2.end_lineno, c2.end_col_offset) == (2, 7)

        c3 = ast_nodes[2]
        assert isinstance(c3, nodes.Const)
        assert (c3.lineno, c3.col_offset) == (3, 0)
        assert (c3.end_lineno, c3.end_col_offset) == (3, 4)

        c4 = ast_nodes[3]
        assert isinstance(c4, nodes.Const)
        assert (c4.lineno, c4.col_offset) == (4, 0)
        assert (c4.end_lineno, c4.end_col_offset) == (4, 4)

        c5 = ast_nodes[4]
        assert isinstance(c5, nodes.Const)
        assert (c5.lineno, c5.col_offset) == (5, 0)
        assert (c5.end_lineno, c5.end_col_offset) == (5, 5)

        c6 = ast_nodes[5]
        assert isinstance(c6, nodes.Const)
        assert (c6.lineno, c6.col_offset) == (6, 0)
        assert (c6.end_lineno, c6.end_col_offset) == (6, 3)

    @staticmethod
    def test_end_lineno_function() -> None:
        """FunctionDef, AsyncFunctionDef, Decorators, Lambda, Arguments."""
        code = textwrap.dedent(
            """
        def func(  #@
            a: int = 0, /,
            var: int = 1, *args: Any,
            keyword: int = 2, **kwargs: Any
        ) -> None:
            pass

        @decorator1
        @decorator2
        async def func():  #@
            pass

        lambda x: 2  #@
        """
        ).strip()
        ast_nodes = builder.extract_node(code)
        assert isinstance(ast_nodes, list) and len(ast_nodes) == 3

        # fmt: off
        f1 = ast_nodes[0]
        assert isinstance(f1, nodes.FunctionDef)
        assert isinstance(f1.args, nodes.Arguments)
        assert isinstance(f1.returns, nodes.Const)
        assert isinstance(f1.body[0], nodes.Pass)
        assert (f1.lineno, f1.col_offset) == (1, 0)
        assert (f1.end_lineno, f1.end_col_offset) == (6, 8)
        assert (f1.returns.lineno, f1.returns.col_offset) == (5, 5)
        assert (f1.returns.end_lineno, f1.returns.end_col_offset) == (5, 9)
        assert (f1.body[0].lineno, f1.body[0].col_offset) == (6, 4)
        assert (f1.body[0].end_lineno, f1.body[0].end_col_offset) == (6, 8)

        # pos only arguments
        # TODO fix column offset: arg -> arg (AssignName)
        assert isinstance(f1.args.posonlyargs[0], nodes.AssignName)
        assert (f1.args.posonlyargs[0].lineno, f1.args.posonlyargs[0].col_offset) == (2, 4)
        assert (f1.args.posonlyargs[0].end_lineno, f1.args.posonlyargs[0].end_col_offset) == (2, 10)
        assert isinstance(f1.args.posonlyargs_annotations[0], nodes.Name)
        assert (
            f1.args.posonlyargs_annotations[0].lineno, f1.args.posonlyargs_annotations[0].col_offset
        ) == (2, 7)
        assert (
            f1.args.posonlyargs_annotations[0].end_lineno, f1.args.posonlyargs_annotations[0].end_col_offset
        ) == (2, 10)
        assert (f1.args.defaults[0].lineno, f1.args.defaults[0].col_offset) == (2, 13)
        assert (f1.args.defaults[0].end_lineno, f1.args.defaults[0].end_col_offset) == (2, 14)

        # pos or kw arguments
        assert isinstance(f1.args.args[0], nodes.AssignName)
        assert (f1.args.args[0].lineno, f1.args.args[0].col_offset) == (3, 4)
        assert (f1.args.args[0].end_lineno, f1.args.args[0].end_col_offset) == (3, 12)
        assert isinstance(f1.args.annotations[0], nodes.Name)
        assert (f1.args.annotations[0].lineno, f1.args.annotations[0].col_offset) == (3, 9)
        assert (f1.args.annotations[0].end_lineno, f1.args.annotations[0].end_col_offset) == (3, 12)
        assert isinstance(f1.args.defaults[1], nodes.Const)
        assert (f1.args.defaults[1].lineno, f1.args.defaults[1].col_offset) == (3, 15)
        assert (f1.args.defaults[1].end_lineno, f1.args.defaults[1].end_col_offset) == (3, 16)

        # *args
        assert isinstance(f1.args.varargannotation, nodes.Name)
        assert (f1.args.varargannotation.lineno, f1.args.varargannotation.col_offset) == (3, 25)
        assert (f1.args.varargannotation.end_lineno, f1.args.varargannotation.end_col_offset) == (3, 28)

        # kw_only arguments
        assert isinstance(f1.args.kwonlyargs[0], nodes.AssignName)
        assert (f1.args.kwonlyargs[0].lineno, f1.args.kwonlyargs[0].col_offset) == (4, 4)
        assert (f1.args.kwonlyargs[0].end_lineno, f1.args.kwonlyargs[0].end_col_offset) == (4, 16)
        annotations = f1.args.kwonlyargs_annotations
        assert isinstance(annotations[0], nodes.Name)
        assert (annotations[0].lineno, annotations[0].col_offset) == (4, 13)
        assert (annotations[0].end_lineno, annotations[0].end_col_offset) == (4, 16)
        assert isinstance(f1.args.kw_defaults[0], nodes.Const)
        assert (f1.args.kw_defaults[0].lineno, f1.args.kw_defaults[0].col_offset) == (4, 19)
        assert (f1.args.kw_defaults[0].end_lineno, f1.args.kw_defaults[0].end_col_offset) == (4, 20)

        # **kwargs
        assert isinstance(f1.args.kwargannotation, nodes.Name)
        assert (f1.args.kwargannotation.lineno, f1.args.kwargannotation.col_offset) == (4, 32)
        assert (f1.args.kwargannotation.end_lineno, f1.args.kwargannotation.end_col_offset) == (4, 35)

        f2 = ast_nodes[1]
        assert isinstance(f2, nodes.AsyncFunctionDef)
        assert isinstance(f2.decorators, nodes.Decorators)
        assert isinstance(f2.decorators.nodes[0], nodes.Name)
        assert isinstance(f2.decorators.nodes[1], nodes.Name)
        assert (f2.lineno, f2.col_offset) == (8, 0)
        assert (f2.end_lineno, f2.end_col_offset) == (11, 8)
        assert (f2.decorators.lineno, f2.decorators.col_offset) == (8, 0)
        assert (f2.decorators.end_lineno, f2.decorators.end_col_offset) == (9, 11)
        assert (f2.decorators.nodes[0].lineno, f2.decorators.nodes[0].col_offset) == (8, 1)
        assert (f2.decorators.nodes[0].end_lineno, f2.decorators.nodes[0].end_col_offset) == (8, 11)
        assert (f2.decorators.nodes[1].lineno, f2.decorators.nodes[1].col_offset) == (9, 1)
        assert (f2.decorators.nodes[1].end_lineno, f2.decorators.nodes[1].end_col_offset) == (9, 11)

        f3 = ast_nodes[2]
        assert isinstance(f3, nodes.Lambda)
        assert isinstance(f3.args, nodes.Arguments)
        assert isinstance(f3.args.args[0], nodes.AssignName)
        assert isinstance(f3.body, nodes.Const)
        assert (f3.lineno, f3.col_offset) == (13, 0)
        assert (f3.end_lineno, f3.end_col_offset) == (13, 11)
        assert (f3.args.args[0].lineno, f3.args.args[0].col_offset) == (13, 7)
        assert (f3.args.args[0].end_lineno, f3.args.args[0].end_col_offset) == (13, 8)
        assert (f3.body.lineno, f3.body.col_offset) == (13, 10)
        assert (f3.body.end_lineno, f3.body.end_col_offset) == (13, 11)
        # fmt: on

    @staticmethod
    def test_end_lineno_dict() -> None:
        """Dict, DictUnpack."""
        code = textwrap.dedent(
            """
        {  #@
            1: "Hello",
            **{2: "World"}  #@
        }
        """
        ).strip()
        ast_nodes = builder.extract_node(code)
        assert isinstance(ast_nodes, list) and len(ast_nodes) == 2

        d1 = ast_nodes[0]
        assert isinstance(d1, nodes.Dict)
        assert isinstance(d1.items[0][0], nodes.Const)
        assert isinstance(d1.items[0][1], nodes.Const)
        assert (d1.lineno, d1.col_offset) == (1, 0)
        assert (d1.end_lineno, d1.end_col_offset) == (4, 1)
        assert (d1.items[0][0].lineno, d1.items[0][0].col_offset) == (2, 4)
        assert (d1.items[0][0].end_lineno, d1.items[0][0].end_col_offset) == (2, 5)
        assert (d1.items[0][1].lineno, d1.items[0][1].col_offset) == (2, 7)
        assert (d1.items[0][1].end_lineno, d1.items[0][1].end_col_offset) == (2, 14)

        d2 = ast_nodes[1]
        assert isinstance(d2, nodes.DictUnpack)
        assert (d2.lineno, d2.col_offset) == (3, 6)
        assert (d2.end_lineno, d2.end_col_offset) == (3, 18)

    @staticmethod
    def test_end_lineno_try() -> None:
        """Try, ExceptHandler."""
        code = textwrap.dedent(
            """
        try:  #@
            pass
        except KeyError as ex:
            pass
        except AttributeError as ex:
            pass
        else:
            pass

        try:  #@
            pass
        except KeyError as ex:
            pass
        else:
            pass
        finally:
            pass
        """
        ).strip()
        ast_nodes = builder.extract_node(code)
        assert isinstance(ast_nodes, list) and len(ast_nodes) == 2

        t1 = ast_nodes[0]
        assert isinstance(t1, nodes.Try)
        assert isinstance(t1.body[0], nodes.Pass)
        assert isinstance(t1.orelse[0], nodes.Pass)
        assert (t1.lineno, t1.col_offset) == (1, 0)
        assert (t1.end_lineno, t1.end_col_offset) == (8, 8)
        assert (t1.body[0].lineno, t1.body[0].col_offset) == (2, 4)
        assert (t1.body[0].end_lineno, t1.body[0].end_col_offset) == (2, 8)
        assert (t1.orelse[0].lineno, t1.orelse[0].col_offset) == (8, 4)
        assert (t1.orelse[0].end_lineno, t1.orelse[0].end_col_offset) == (8, 8)

        t2 = t1.handlers[0]
        assert isinstance(t2, nodes.ExceptHandler)
        assert isinstance(t2.type, nodes.Name)
        assert isinstance(t2.name, nodes.AssignName)
        assert isinstance(t2.body[0], nodes.Pass)
        assert (t2.lineno, t2.col_offset) == (3, 0)
        assert (t2.end_lineno, t2.end_col_offset) == (4, 8)
        assert (t2.type.lineno, t2.type.col_offset) == (3, 7)
        assert (t2.type.end_lineno, t2.type.end_col_offset) == (3, 15)
        # TODO fix column offset: ExceptHandler -> name (AssignName)
        assert (t2.name.lineno, t2.name.col_offset) == (3, 0)
        assert (t2.name.end_lineno, t2.name.end_col_offset) == (4, 8)
        assert (t2.body[0].lineno, t2.body[0].col_offset) == (4, 4)
        assert (t2.body[0].end_lineno, t2.body[0].end_col_offset) == (4, 8)

        t3 = ast_nodes[1]
        assert isinstance(t3, nodes.Try)
        assert isinstance(t3.finalbody[0], nodes.Pass)
        assert (t3.lineno, t3.col_offset) == (10, 0)
        assert (t3.end_lineno, t3.end_col_offset) == (17, 8)
        assert (t3.body[0].lineno, t3.body[0].col_offset) == (11, 4)
        assert (t3.body[0].end_lineno, t3.body[0].end_col_offset) == (11, 8)
        assert (t3.finalbody[0].lineno, t3.finalbody[0].col_offset) == (17, 4)
        assert (t3.finalbody[0].end_lineno, t3.finalbody[0].end_col_offset) == (17, 8)

    @staticmethod
    def test_end_lineno_subscript() -> None:
        """Subscript, Slice, (ExtSlice, Index)."""
        code = textwrap.dedent(
            """
        var[0]  #@
        var[1:2:1]  #@
        var[1:2, 2]  #@
        """
        ).strip()
        ast_nodes = builder.extract_node(code)
        assert isinstance(ast_nodes, list) and len(ast_nodes) == 3

        s1 = ast_nodes[0]
        assert isinstance(s1, nodes.Subscript)
        assert isinstance(s1.value, nodes.Name)
        assert isinstance(s1.slice, nodes.Const)
        assert (s1.lineno, s1.col_offset) == (1, 0)
        assert (s1.end_lineno, s1.end_col_offset) == (1, 6)
        assert (s1.value.lineno, s1.value.col_offset) == (1, 0)
        assert (s1.value.end_lineno, s1.value.end_col_offset) == (1, 3)
        assert (s1.slice.lineno, s1.slice.col_offset) == (1, 4)
        assert (s1.slice.end_lineno, s1.slice.end_col_offset) == (1, 5)

        s2 = ast_nodes[1]
        assert isinstance(s2, nodes.Subscript)
        assert isinstance(s2.slice, nodes.Slice)
        assert isinstance(s2.slice.lower, nodes.Const)
        assert isinstance(s2.slice.upper, nodes.Const)
        assert isinstance(s2.slice.step, nodes.Const)
        assert (s2.lineno, s2.col_offset) == (2, 0)
        assert (s2.end_lineno, s2.end_col_offset) == (2, 10)
        assert (s2.slice.lower.lineno, s2.slice.lower.col_offset) == (2, 4)
        assert (s2.slice.lower.end_lineno, s2.slice.lower.end_col_offset) == (2, 5)
        assert (s2.slice.upper.lineno, s2.slice.upper.col_offset) == (2, 6)
        assert (s2.slice.upper.end_lineno, s2.slice.upper.end_col_offset) == (2, 7)
        assert (s2.slice.step.lineno, s2.slice.step.col_offset) == (2, 8)
        assert (s2.slice.step.end_lineno, s2.slice.step.end_col_offset) == (2, 9)

        s3 = ast_nodes[2]
        assert isinstance(s3, nodes.Subscript)
        assert isinstance(s3.slice, nodes.Tuple)
        assert (s3.lineno, s3.col_offset) == (3, 0)
        assert (s3.end_lineno, s3.end_col_offset) == (3, 11)
        assert (s3.slice.lineno, s3.slice.col_offset) == (3, 4)
        assert (s3.slice.end_lineno, s3.slice.end_col_offset) == (3, 10)

    @staticmethod
    def test_end_lineno_import() -> None:
        """Import, ImportFrom."""
        code = textwrap.dedent(
            """
        import a.b  #@
        import a as x  #@
        from . import x  #@
        from .a import y as y  #@
        """
        ).strip()
        ast_nodes = builder.extract_node(code)
        assert isinstance(ast_nodes, list) and len(ast_nodes) == 4

        i1 = ast_nodes[0]
        assert isinstance(i1, nodes.Import)
        assert (i1.lineno, i1.col_offset) == (1, 0)
        assert (i1.end_lineno, i1.end_col_offset) == (1, 10)

        i2 = ast_nodes[1]
        assert isinstance(i2, nodes.Import)
        assert (i2.lineno, i2.col_offset) == (2, 0)
        assert (i2.end_lineno, i2.end_col_offset) == (2, 13)

        i3 = ast_nodes[2]
        assert isinstance(i3, nodes.ImportFrom)
        assert (i3.lineno, i3.col_offset) == (3, 0)
        assert (i3.end_lineno, i3.end_col_offset) == (3, 15)

        i4 = ast_nodes[3]
        assert isinstance(i4, nodes.ImportFrom)
        assert (i4.lineno, i4.col_offset) == (4, 0)
        assert (i4.end_lineno, i4.end_col_offset) == (4, 21)

    @staticmethod
    def test_end_lineno_with() -> None:
        """With, AsyncWith."""
        code = textwrap.dedent(
            """
        with open(file) as fp, \\
                open(file2) as fp2:  #@
            pass

        async with open(file) as fp:  #@
            pass
        """
        ).strip()
        ast_nodes = builder.extract_node(code)
        assert isinstance(ast_nodes, list) and len(ast_nodes) == 2

        w1 = ast_nodes[0].parent
        assert isinstance(w1, nodes.With)
        assert isinstance(w1.items[0][0], nodes.Call)
        assert isinstance(w1.items[0][1], nodes.AssignName)
        assert isinstance(w1.items[1][0], nodes.Call)
        assert isinstance(w1.items[1][1], nodes.AssignName)
        assert isinstance(w1.body[0], nodes.Pass)
        assert (w1.lineno, w1.col_offset) == (1, 0)
        assert (w1.end_lineno, w1.end_col_offset) == (3, 8)
        assert (w1.items[0][0].lineno, w1.items[0][0].col_offset) == (1, 5)
        assert (w1.items[0][0].end_lineno, w1.items[0][0].end_col_offset) == (1, 15)
        assert (w1.items[0][1].lineno, w1.items[0][1].col_offset) == (1, 19)
        assert (w1.items[0][1].end_lineno, w1.items[0][1].end_col_offset) == (1, 21)
        assert (w1.items[1][0].lineno, w1.items[1][0].col_offset) == (2, 8)
        assert (w1.items[1][0].end_lineno, w1.items[1][0].end_col_offset) == (2, 19)
        assert (w1.items[1][1].lineno, w1.items[1][1].col_offset) == (2, 23)
        assert (w1.items[1][1].end_lineno, w1.items[1][1].end_col_offset) == (2, 26)
        assert (w1.body[0].lineno, w1.body[0].col_offset) == (3, 4)
        assert (w1.body[0].end_lineno, w1.body[0].end_col_offset) == (3, 8)

        w2 = ast_nodes[1]
        assert isinstance(w2, nodes.AsyncWith)
        assert isinstance(w2.items[0][0], nodes.Call)
        assert isinstance(w2.items[0][1], nodes.AssignName)
        assert isinstance(w2.body[0], nodes.Pass)
        assert (w2.lineno, w2.col_offset) == (5, 0)
        assert (w2.end_lineno, w2.end_col_offset) == (6, 8)
        assert (w2.items[0][0].lineno, w2.items[0][0].col_offset) == (5, 11)
        assert (w2.items[0][0].end_lineno, w2.items[0][0].end_col_offset) == (5, 21)
        assert (w2.items[0][1].lineno, w2.items[0][1].col_offset) == (5, 25)
        assert (w2.items[0][1].end_lineno, w2.items[0][1].end_col_offset) == (5, 27)
        assert (w2.body[0].lineno, w2.body[0].col_offset) == (6, 4)
        assert (w2.body[0].end_lineno, w2.body[0].end_col_offset) == (6, 8)

    @staticmethod
    def test_end_lineno_while() -> None:
        """While."""
        code = textwrap.dedent(
            """
        while 2:
            pass
        else:
            pass
        """
        ).strip()
        w1 = builder.extract_node(code)
        assert isinstance(w1, nodes.While)
        assert isinstance(w1.test, nodes.Const)
        assert isinstance(w1.body[0], nodes.Pass)
        assert isinstance(w1.orelse[0], nodes.Pass)
        assert (w1.lineno, w1.col_offset) == (1, 0)
        assert (w1.end_lineno, w1.end_col_offset) == (4, 8)
        assert (w1.test.lineno, w1.test.col_offset) == (1, 6)
        assert (w1.test.end_lineno, w1.test.end_col_offset) == (1, 7)
        assert (w1.body[0].lineno, w1.body[0].col_offset) == (2, 4)
        assert (w1.body[0].end_lineno, w1.body[0].end_col_offset) == (2, 8)
        assert (w1.orelse[0].lineno, w1.orelse[0].col_offset) == (4, 4)
        assert (w1.orelse[0].end_lineno, w1.orelse[0].end_col_offset) == (4, 8)

    @staticmethod
    def test_end_lineno_string() -> None:
        """FormattedValue, JoinedStr."""
        code = textwrap.dedent(
            """
        f"Hello World: {42.1234:02d}"  #@
        f"Hello: {name=}"  #@
        """
        ).strip()
        ast_nodes = builder.extract_node(code)
        assert isinstance(ast_nodes, list) and len(ast_nodes) == 2

        s1 = ast_nodes[0]
        assert isinstance(s1, nodes.JoinedStr)
        assert isinstance(s1.values[0], nodes.Const)
        assert (s1.lineno, s1.col_offset) == (1, 0)
        assert (s1.end_lineno, s1.end_col_offset) == (1, 29)
        if PY312_PLUS:
            assert (s1.values[0].lineno, s1.values[0].col_offset) == (1, 2)
            assert (s1.values[0].end_lineno, s1.values[0].end_col_offset) == (1, 15)
        else:
            # Bug in Python 3.11
            # https://github.com/python/cpython/issues/81639
            assert (s1.values[0].lineno, s1.values[0].col_offset) == (1, 0)
            assert (s1.values[0].end_lineno, s1.values[0].end_col_offset) == (1, 29)

        s2 = s1.values[1]
        assert isinstance(s2, nodes.FormattedValue)
        if PY312_PLUS:
            assert (s2.lineno, s2.col_offset) == (1, 15)
            assert (s2.end_lineno, s2.end_col_offset) == (1, 28)
        else:
            assert (s2.lineno, s2.col_offset) == (1, 0)
            assert (s2.end_lineno, s2.end_col_offset) == (1, 29)

        assert isinstance(s2.value, nodes.Const)  # 42.1234
        assert (s2.value.lineno, s2.value.col_offset) == (1, 16)
        assert (s2.value.end_lineno, s2.value.end_col_offset) == (1, 23)
        assert isinstance(s2.format_spec, nodes.JoinedStr)  # ':02d'
        if PY312_PLUS:
            assert (s2.format_spec.lineno, s2.format_spec.col_offset) == (1, 23)
            assert (s2.format_spec.end_lineno, s2.format_spec.end_col_offset) == (1, 27)
        else:
            assert (s2.format_spec.lineno, s2.format_spec.col_offset) == (1, 0)
            assert (s2.format_spec.end_lineno, s2.format_spec.end_col_offset) == (1, 29)

        s3 = ast_nodes[1]
        assert isinstance(s3, nodes.JoinedStr)
        assert isinstance(s3.values[0], nodes.Const)
        assert (s3.lineno, s3.col_offset) == (2, 0)
        assert (s3.end_lineno, s3.end_col_offset) == (2, 17)
        if PY312_PLUS:
            assert (s3.values[0].lineno, s3.values[0].col_offset) == (2, 2)
            assert (s3.values[0].end_lineno, s3.values[0].end_col_offset) == (2, 15)
        else:
            assert (s3.values[0].lineno, s3.values[0].col_offset) == (2, 0)
            assert (s3.values[0].end_lineno, s3.values[0].end_col_offset) == (2, 17)

        s4 = s3.values[1]
        assert isinstance(s4, nodes.FormattedValue)
        if PY312_PLUS:
            assert (s4.lineno, s4.col_offset) == (2, 9)
            assert (s4.end_lineno, s4.end_col_offset) == (2, 16)
        else:
            assert (s4.lineno, s4.col_offset) == (2, 0)
            assert (s4.end_lineno, s4.end_col_offset) == (2, 17)

        assert isinstance(s4.value, nodes.Name)  # 'name'
        assert (s4.value.lineno, s4.value.col_offset) == (2, 10)
        assert (s4.value.end_lineno, s4.value.end_col_offset) == (2, 14)

    @staticmethod
    @pytest.mark.skipif(not PY310_PLUS, reason="pattern matching was added in PY310")
    def test_end_lineno_match() -> None:
        """Match, MatchValue, MatchSingleton, MatchSequence, MatchMapping,
        MatchClass, MatchStar, MatchOr, MatchAs.
        """
        code = textwrap.dedent(
            """
        match x:  #@
            case 200 if True:  #@
                pass
            case True:  #@
                pass
            case (1, 2, *args): #@
                pass
            case {1: "Hello", **rest}: #@
                pass
            case Point2d(0, y=0):  #@
                pass
            case 200 | 300:  #@
                pass
            case 200 as c:  #@
                pass
        """
        ).strip()
        ast_nodes = builder.extract_node(code)
        assert isinstance(ast_nodes, list) and len(ast_nodes) == 8

        # fmt: off
        m1 = ast_nodes[0]
        assert isinstance(m1, nodes.Match)
        assert (m1.lineno, m1.col_offset) == (1, 0)
        assert (m1.end_lineno, m1.end_col_offset) == (15, 12)
        assert (m1.subject.lineno, m1.subject.col_offset) == (1, 6)
        assert (m1.subject.end_lineno, m1.subject.end_col_offset) == (1, 7)

        m2 = ast_nodes[1]
        assert isinstance(m2, nodes.MatchCase)
        assert isinstance(m2.pattern, nodes.MatchValue)
        assert isinstance(m2.guard, nodes.Const)
        assert isinstance(m2.body[0], nodes.Pass)
        assert (m2.pattern.lineno, m2.pattern.col_offset) == (2, 9)
        assert (m2.pattern.end_lineno, m2.pattern.end_col_offset) == (2, 12)
        assert (m2.guard.lineno, m2.guard.col_offset) == (2, 16)
        assert (m2.guard.end_lineno, m2.guard.end_col_offset) == (2, 20)
        assert (m2.body[0].lineno, m2.body[0].col_offset) == (3, 8)
        assert (m2.body[0].end_lineno, m2.body[0].end_col_offset) == (3, 12)

        m3 = ast_nodes[2]
        assert isinstance(m3, nodes.MatchCase)
        assert isinstance(m3.pattern, nodes.MatchSingleton)
        assert (m3.pattern.lineno, m3.pattern.col_offset) == (4, 9)
        assert (m3.pattern.end_lineno, m3.pattern.end_col_offset) == (4, 13)

        m4 = ast_nodes[3]
        assert isinstance(m4, nodes.MatchCase)
        assert isinstance(m4.pattern, nodes.MatchSequence)
        assert isinstance(m4.pattern.patterns[0], nodes.MatchValue)
        assert (m4.pattern.lineno, m4.pattern.col_offset) == (6, 9)
        assert (m4.pattern.end_lineno, m4.pattern.end_col_offset) == (6, 22)
        assert (m4.pattern.patterns[0].lineno, m4.pattern.patterns[0].col_offset) == (6, 10)
        assert (m4.pattern.patterns[0].end_lineno, m4.pattern.patterns[0].end_col_offset) == (6, 11)

        m5 = m4.pattern.patterns[2]
        assert isinstance(m5, nodes.MatchStar)
        assert isinstance(m5.name, nodes.AssignName)
        assert (m5.lineno, m5.col_offset) == (6, 16)
        assert (m5.end_lineno, m5.end_col_offset) == (6, 21)
        # TODO fix column offset: MatchStar -> name (AssignName)
        assert (m5.name.lineno, m5.name.col_offset) == (6, 16)
        assert (m5.name.end_lineno, m5.name.end_col_offset) == (6, 21)

        m6 = ast_nodes[4]
        assert isinstance(m6, nodes.MatchCase)
        assert isinstance(m6.pattern, nodes.MatchMapping)
        assert isinstance(m6.pattern.keys[0], nodes.Const)
        assert isinstance(m6.pattern.patterns[0], nodes.MatchValue)
        assert isinstance(m6.pattern.rest, nodes.AssignName)
        assert (m6.pattern.lineno, m6.pattern.col_offset) == (8, 9)
        assert (m6.pattern.end_lineno, m6.pattern.end_col_offset) == (8, 29)
        assert (m6.pattern.keys[0].lineno, m6.pattern.keys[0].col_offset) == (8, 10)
        assert (m6.pattern.keys[0].end_lineno, m6.pattern.keys[0].end_col_offset) == (8, 11)
        assert (m6.pattern.patterns[0].lineno, m6.pattern.patterns[0].col_offset) == (8, 13)
        assert (m6.pattern.patterns[0].end_lineno, m6.pattern.patterns[0].end_col_offset) == (8, 20)
        # TODO fix column offset: MatchMapping -> rest (AssignName)
        assert (m6.pattern.rest.lineno, m6.pattern.rest.col_offset) == (8, 9)
        assert (m6.pattern.rest.end_lineno, m6.pattern.rest.end_col_offset) == (8, 29)

        m7 = ast_nodes[5]
        assert isinstance(m7, nodes.MatchCase)
        assert isinstance(m7.pattern, nodes.MatchClass)
        assert isinstance(m7.pattern.cls, nodes.Name)
        assert isinstance(m7.pattern.patterns[0], nodes.MatchValue)
        assert isinstance(m7.pattern.kwd_patterns[0], nodes.MatchValue)
        assert (m7.pattern.lineno, m7.pattern.col_offset) == (10, 9)
        assert (m7.pattern.end_lineno, m7.pattern.end_col_offset) == (10, 24)
        assert (m7.pattern.cls.lineno, m7.pattern.cls.col_offset) == (10, 9)
        assert (m7.pattern.cls.end_lineno, m7.pattern.cls.end_col_offset) == (10, 16)
        assert (m7.pattern.patterns[0].lineno, m7.pattern.patterns[0].col_offset) == (10, 17)
        assert (m7.pattern.patterns[0].end_lineno, m7.pattern.patterns[0].end_col_offset) == (10, 18)
        assert (m7.pattern.kwd_patterns[0].lineno, m7.pattern.kwd_patterns[0].col_offset) == (10, 22)
        assert (m7.pattern.kwd_patterns[0].end_lineno, m7.pattern.kwd_patterns[0].end_col_offset) == (10, 23)

        m8 = ast_nodes[6]
        assert isinstance(m8, nodes.MatchCase)
        assert isinstance(m8.pattern, nodes.MatchOr)
        assert isinstance(m8.pattern.patterns[0], nodes.MatchValue)
        assert (m8.pattern.lineno, m8.pattern.col_offset) == (12, 9)
        assert (m8.pattern.end_lineno, m8.pattern.end_col_offset) == (12, 18)
        assert (m8.pattern.patterns[0].lineno, m8.pattern.patterns[0].col_offset) == (12, 9)
        assert (m8.pattern.patterns[0].end_lineno, m8.pattern.patterns[0].end_col_offset) == (12, 12)

        m9 = ast_nodes[7]
        assert isinstance(m9, nodes.MatchCase)
        assert isinstance(m9.pattern, nodes.MatchAs)
        assert isinstance(m9.pattern.pattern, nodes.MatchValue)
        assert isinstance(m9.pattern.name, nodes.AssignName)
        assert (m9.pattern.lineno, m9.pattern.col_offset) == (14, 9)
        assert (m9.pattern.end_lineno, m9.pattern.end_col_offset) == (14, 17)
        assert (m9.pattern.pattern.lineno, m9.pattern.pattern.col_offset) == (14, 9)
        assert (m9.pattern.pattern.end_lineno, m9.pattern.pattern.end_col_offset) == (14, 12)
        # TODO fix column offset: MatchAs -> name (AssignName)
        assert (m9.pattern.name.lineno, m9.pattern.name.col_offset) == (14, 9)
        assert (m9.pattern.name.end_lineno, m9.pattern.name.end_col_offset) == (14, 17)
        # fmt: on

    @staticmethod
    def test_end_lineno_comprehension() -> None:
        """ListComp, SetComp, DictComp, GeneratorExpr."""
        code = textwrap.dedent(
            """
        [x for x in var]  #@
        {x for x in var}  #@
        {x: y for x, y in var}  #@
        (x for x in var)  #@
        """
        ).strip()
        ast_nodes = builder.extract_node(code)
        assert isinstance(ast_nodes, list) and len(ast_nodes) == 4

        c1 = ast_nodes[0]
        assert isinstance(c1, nodes.ListComp)
        assert isinstance(c1.elt, nodes.Name)
        assert isinstance(c1.generators[0], nodes.Comprehension)  # type: ignore[index]
        assert (c1.lineno, c1.col_offset) == (1, 0)
        assert (c1.end_lineno, c1.end_col_offset) == (1, 16)
        assert (c1.elt.lineno, c1.elt.col_offset) == (1, 1)
        assert (c1.elt.end_lineno, c1.elt.end_col_offset) == (1, 2)

        c2 = ast_nodes[1]
        assert isinstance(c2, nodes.SetComp)
        assert isinstance(c2.elt, nodes.Name)
        assert isinstance(c2.generators[0], nodes.Comprehension)  # type: ignore[index]
        assert (c2.lineno, c2.col_offset) == (2, 0)
        assert (c2.end_lineno, c2.end_col_offset) == (2, 16)
        assert (c2.elt.lineno, c2.elt.col_offset) == (2, 1)
        assert (c2.elt.end_lineno, c2.elt.end_col_offset) == (2, 2)

        c3 = ast_nodes[2]
        assert isinstance(c3, nodes.DictComp)
        assert isinstance(c3.key, nodes.Name)
        assert isinstance(c3.value, nodes.Name)
        assert isinstance(c3.generators[0], nodes.Comprehension)  # type: ignore[index]
        assert (c3.lineno, c3.col_offset) == (3, 0)
        assert (c3.end_lineno, c3.end_col_offset) == (3, 22)
        assert (c3.key.lineno, c3.key.col_offset) == (3, 1)
        assert (c3.key.end_lineno, c3.key.end_col_offset) == (3, 2)
        assert (c3.value.lineno, c3.value.col_offset) == (3, 4)
        assert (c3.value.end_lineno, c3.value.end_col_offset) == (3, 5)

        c4 = ast_nodes[3]
        assert isinstance(c4, nodes.GeneratorExp)
        assert isinstance(c4.elt, nodes.Name)
        assert isinstance(c4.generators[0], nodes.Comprehension)  # type: ignore[index]
        assert (c4.lineno, c4.col_offset) == (4, 0)
        assert (c4.end_lineno, c4.end_col_offset) == (4, 16)
        assert (c4.elt.lineno, c4.elt.col_offset) == (4, 1)
        assert (c4.elt.end_lineno, c4.elt.end_col_offset) == (4, 2)

    @staticmethod
    def test_end_lineno_class() -> None:
        """ClassDef, Keyword."""
        code = textwrap.dedent(
            """
        @decorator1
        @decorator2
        class X(Parent, var=42):
            pass
        """
        ).strip()
        c1 = builder.extract_node(code)
        assert isinstance(c1, nodes.ClassDef)
        assert isinstance(c1.decorators, nodes.Decorators)
        assert isinstance(c1.bases[0], nodes.Name)
        assert isinstance(c1.keywords[0], nodes.Keyword)
        assert isinstance(c1.body[0], nodes.Pass)

        # fmt: off
        assert (c1.lineno, c1.col_offset) == (3, 0)
        assert (c1.end_lineno, c1.end_col_offset) == (4, 8)
        assert (c1.decorators.lineno, c1.decorators.col_offset) == (1, 0)
        assert (c1.decorators.end_lineno, c1.decorators.end_col_offset) == (2, 11)
        assert (c1.bases[0].lineno, c1.bases[0].col_offset) == (3, 8)
        assert (c1.bases[0].end_lineno, c1.bases[0].end_col_offset) == (3, 14)
        assert (c1.keywords[0].lineno, c1.keywords[0].col_offset) == (3, 16)
        assert (c1.keywords[0].end_lineno, c1.keywords[0].end_col_offset) == (3, 22)
        assert (c1.body[0].lineno, c1.body[0].col_offset) == (4, 4)
        assert (c1.body[0].end_lineno, c1.body[0].end_col_offset) == (4, 8)
        # fmt: on

    @staticmethod
    def test_end_lineno_module() -> None:
        """Tests for Module."""
        code = """print()"""
        module = astroid.parse(code)
        assert isinstance(module, nodes.Module)
        assert module.lineno == 0
        assert module.col_offset == 0
        assert module.end_lineno is None
        assert module.end_col_offset is None
