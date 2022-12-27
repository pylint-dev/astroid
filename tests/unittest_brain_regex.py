
import unittest

try:
    import regex

    HAS_REGEX = True
except ImportError:
    HAS_REGEX = False

from astroid import MANAGER, builder, nodes, test_utils
from astroid.exceptions import (
    AttributeInferenceError,
    InferenceError,
)


@unittest.skipUnless(HAS_REGEX, "This test requires the regex library.")
class RegexBrainTest(unittest.TestCase):
    def test_regex_flags(self) -> None:
        names = [name for name in dir(regex) if name.isupper()]
        re_ast = MANAGER.ast_from_module_name("regex")
        for name in names:
            self.assertIn(name, re_ast)
            self.assertEqual(next(re_ast[name].infer()).value, getattr(regex, name))

    def test_re_pattern_subscriptable(self):
        """Test regex.Pattern and regex.Match are subscriptable in PY39+"""
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
