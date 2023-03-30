# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import textwrap

from astroid import builder, nodes


class TestNodePosition:
    """Test node ``position`` attribute."""

    @staticmethod
    def test_position_class() -> None:
        """Position should only include keyword and name.

        >>> class A(Parent):
        >>> ^^^^^^^
        """
        code = textwrap.dedent(
            """
        class A:  #@
            ...

        class B(A):  #@
            pass

        class C:  #@
            '''Docstring'''

            class D:  #@
                ...

        class E:  #@
            def f():
                ...

        @decorator
        class F:  #@
            ...
        """
        ).strip()
        ast_nodes: list[nodes.NodeNG] = builder.extract_node(code)  # type: ignore[assignment]

        a = ast_nodes[0]
        assert isinstance(a, nodes.ClassDef)
        assert a.position == (1, 0, 1, 7)

        b = ast_nodes[1]
        assert isinstance(b, nodes.ClassDef)
        assert b.position == (4, 0, 4, 7)

        c = ast_nodes[2]
        assert isinstance(c, nodes.ClassDef)
        assert c.position == (7, 0, 7, 7)

        d = ast_nodes[3]
        assert isinstance(d, nodes.ClassDef)
        assert d.position == (10, 4, 10, 11)

        e = ast_nodes[4]
        assert isinstance(e, nodes.ClassDef)
        assert e.position == (13, 0, 13, 7)

        f = ast_nodes[5]
        assert isinstance(f, nodes.ClassDef)
        assert f.position == (18, 0, 18, 7)

    @staticmethod
    def test_position_function() -> None:
        """Position should only include keyword and name.

        >>> def func(var: int = 42):
        >>> ^^^^^^^^
        """
        code = textwrap.dedent(
            """
        def a():  #@
            ...

        def b():  #@
            '''Docstring'''

        def c(  #@
            var: int = 42
        ):
            def d():  #@
                ...

        @decorator
        def e():  #@
            ...
        """
        ).strip()
        ast_nodes: list[nodes.NodeNG] = builder.extract_node(code)  # type: ignore[assignment]

        a = ast_nodes[0]
        assert isinstance(a, nodes.FunctionDef)
        assert a.position == (1, 0, 1, 5)

        b = ast_nodes[1]
        assert isinstance(b, nodes.FunctionDef)
        assert b.position == (4, 0, 4, 5)

        c = ast_nodes[2]
        assert isinstance(c, nodes.FunctionDef)
        assert c.position == (7, 0, 7, 5)

        d = ast_nodes[3]
        assert isinstance(d, nodes.FunctionDef)
        assert d.position == (10, 4, 10, 9)

        e = ast_nodes[4]
        assert isinstance(e, nodes.FunctionDef)
        assert e.position == (14, 0, 14, 5)

    @staticmethod
    def test_position_async_function() -> None:
        """Position should only include keyword and name.

        >>> async def func(var: int = 42):
        >>> ^^^^^^^^^^^^^^
        """
        code = textwrap.dedent(
            """
        async def a():  #@
            ...

        async def b():  #@
            '''Docstring'''

        async def c(  #@
            var: int = 42
        ):
            async def d():  #@
                ...

        @decorator
        async def e():  #@
            ...
        """
        ).strip()
        ast_nodes: list[nodes.NodeNG] = builder.extract_node(code)  # type: ignore[assignment]

        a = ast_nodes[0]
        assert isinstance(a, nodes.FunctionDef)
        assert a.position == (1, 0, 1, 11)

        b = ast_nodes[1]
        assert isinstance(b, nodes.FunctionDef)
        assert b.position == (4, 0, 4, 11)

        c = ast_nodes[2]
        assert isinstance(c, nodes.FunctionDef)
        assert c.position == (7, 0, 7, 11)

        d = ast_nodes[3]
        assert isinstance(d, nodes.FunctionDef)
        assert d.position == (10, 4, 10, 15)

        e = ast_nodes[4]
        assert isinstance(e, nodes.FunctionDef)
        assert e.position == (14, 0, 14, 11)
