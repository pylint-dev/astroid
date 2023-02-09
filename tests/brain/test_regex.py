# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

try:
    import regex

    HAS_REGEX = True
except ImportError:
    HAS_REGEX = False

import pytest

from astroid import MANAGER, builder, nodes, test_utils


@pytest.mark.skipif(not HAS_REGEX, reason="This test requires the regex library.")
class TestRegexBrain:
    def test_regex_flags(self) -> None:
        """Test that we have all regex enum flags in the brain."""
        names = [name for name in dir(regex) if name.isupper()]
        re_ast = MANAGER.ast_from_module_name("regex")
        for name in names:
            assert name in re_ast
            assert next(re_ast[name].infer()).value == getattr(regex, name)

    @test_utils.require_version(minver="3.9")
    def test_regex_pattern_and_match_subscriptable(self):
        """Test regex.Pattern and regex.Match are subscriptable in PY39+."""
        node1 = builder.extract_node(
            """
        import regex
        regex.Pattern[str]
        """
        )
        inferred1 = next(node1.infer())
        assert isinstance(inferred1, nodes.ClassDef)
        assert isinstance(inferred1.getattr("__class_getitem__")[0], nodes.FunctionDef)

        node2 = builder.extract_node(
            """
        import regex
        regex.Match[str]
        """
        )
        inferred2 = next(node2.infer())
        assert isinstance(inferred2, nodes.ClassDef)
        assert isinstance(inferred2.getattr("__class_getitem__")[0], nodes.FunctionDef)
