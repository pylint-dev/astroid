# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Tests for modules in the stdlib."""

from astroid import nodes
from astroid.builder import _extract_single_node


class TestSys:
    """Tests for the sys module."""

    def test_sys_builtin_module_names(self) -> None:
        """Test that we can gather the elements of a living tuple object."""
        node = _extract_single_node(
            """
        import sys
        sys.builtin_module_names
        """
        )
        inferred = list(node.infer())
        assert len(inferred) == 1
        assert isinstance(inferred[0], nodes.Tuple)
        assert inferred[0].elts

    def test_sys_modules(self) -> None:
        """Test that we can gather the items of a living dict object."""
        node = _extract_single_node(
            """
        import sys
        sys.modules
        """
        )
        inferred = list(node.infer())
        assert len(inferred) == 1
        assert isinstance(inferred[0], nodes.Dict)
        assert inferred[0].items
