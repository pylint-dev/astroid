# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import unittest

try:
    import gi  # pylint: disable=unused-import

    HAS_GI = True
except ImportError:
    HAS_GI = False

from astroid import builder, nodes


@unittest.skipUnless(HAS_GI, "This test requires the gobject introspection library.")
class GiBrainClassificationTest(unittest.TestCase):
    """Test that gi functions are correctly classified."""

    def _inferred_gi_symbol(self, namespace, version, symbol):
        node = builder.extract_node(
            f"""
        import gi

        gi.require_version("{namespace}", "{version}")
        from gi.repository import {namespace}
        {namespace}.{symbol}
        """
        )
        return node.inferred()

    def test_gi_function_classification(self):
        """Test that global functions are correctly classified without the 'self' argument."""
        inferred = self._inferred_gi_symbol("GLib", "2.0", "get_tmp_dir")
        self.assertEqual(len(inferred), 1)
        self.assertEqual(inferred[0].pytype(), "builtins.function")

        funcdef = inferred[0].frame()
        self.assertIsInstance(funcdef, nodes.FunctionDef)

        args = funcdef.argnames()
        if len(args) > 0:
            self.assertNotEqual(args[0], "self")

    def test_gi_method_classification(self):
        """Test that methods are correctly classified and accept the 'self' argument."""
        inferred = self._inferred_gi_symbol("GLib", "2.0", "String.append")
        self.assertEqual(len(inferred), 1)
        self.assertEqual(inferred[0].pytype(), "builtins.instancemethod")

        funcdef = inferred[0].frame()
        self.assertIsInstance(funcdef, nodes.FunctionDef)

        self.assertIn(
            funcdef.argnames()[0],
            {"self", funcdef.args.vararg},
            "Method does not accept 'self' as first argument",
        )
