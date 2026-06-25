# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import textwrap
from tokenize import TokenError
from unittest import mock

from astroid import builder, nodes


class TestNodePosition:
    """Test node ``position`` attribute."""

    @staticmethod
    def test_position_class() -> None:
        """Position should only include keyword and name.

        >>> class A(Parent):
        >>> ^^^^^^^
        """
        code = textwrap.dedent("""
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
        """).strip()
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
        code = textwrap.dedent("""
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
        """).strip()
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
        code = textwrap.dedent("""
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
        """).strip()
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

    @staticmethod
    def test_position_malformed_tokenize() -> None:
        """A ``TokenError`` from ``tokenize`` must not crash the build.

        On Python < 3.12 malformed source could make ``generate_tokens``
        raise a ``TokenError``; ``position`` is simply unavailable then.
        """
        with mock.patch(
            "astroid.rebuilder.generate_tokens",
            side_effect=TokenError("unexpected EOF in multi-line statement", (1, 0)),
        ):
            node = builder.extract_node("class A:  #@\n    ...")
        assert isinstance(node, nodes.ClassDef)
        assert node.position is None

    @staticmethod
    def test_position_carriage_return_line_endings() -> None:
        """Lines ending in ``\\r`` must not crash the build (#3091).

        The tokenizer treats a lone ``\\r`` as a line terminator while the
        source kept by the rebuilder is split on ``\\n`` only, so the slice
        tokenized for the position can be misaligned and raise
        ``IndentationError``; ``position`` is simply unavailable then.
        """
        module = builder.parse("\rclass C:\n def f():\n  1\n 2")
        klass = module.body[0]
        assert isinstance(klass, nodes.ClassDef)
        func = klass.body[0]
        assert isinstance(func, nodes.FunctionDef)
        assert klass.position is None
        assert func.position is None

    @staticmethod
    def test_position_unnormalized_name() -> None:
        """No position info when the name token never matches ``node.name``.

        ``node.name`` is the NFKC-normalized identifier while ``tokenize``
        yields the raw source spelling (here the ``fi`` ligature), so the
        name token is never matched and no position can be computed.
        """
        node = builder.extract_node("class ﬁ:  #@\n    ...")
        assert isinstance(node, nodes.ClassDef)
        assert node.name == "fi"
        assert node.position is None
