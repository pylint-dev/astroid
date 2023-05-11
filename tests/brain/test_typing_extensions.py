# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import pytest

from astroid import builder, nodes

try:
    import typing_extensions

    HAS_TYPING_EXTENSIONS = True
    HAS_TYPING_EXTENSIONS_TYPEVAR = hasattr(typing_extensions, "TypeVar")
except ImportError:
    HAS_TYPING_EXTENSIONS = False
    HAS_TYPING_EXTENSIONS_TYPEVAR = False


@pytest.mark.skipif(
    not HAS_TYPING_EXTENSIONS,
    reason="These tests require the typing_extensions library",
)
class TestTypingExtensions:
    @staticmethod
    @pytest.mark.skipif(
        not HAS_TYPING_EXTENSIONS_TYPEVAR,
        reason="Need typing_extensions>=4.4.0 to test TypeVar",
    )
    def test_typing_extensions_types() -> None:
        ast_nodes = builder.extract_node(
            """
        from typing_extensions import TypeVar
        TypeVar('MyTypeVar', int, float, complex) #@
        TypeVar('AnyStr', str, bytes) #@
        """
        )
        for node in ast_nodes:
            inferred = next(node.infer())
            assert isinstance(inferred, nodes.ClassDef)
