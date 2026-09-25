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
from astroid.brain.brain_gi import _looks_like_require_version


@unittest.skipUnless(HAS_GI, "This test requires the gobject introspection library.")
class GiBrainClassificationTest(unittest.TestCase):
    """Test that gi functions are correctly classified."""

    def _inferred_gi_symbol(self, namespace, version, symbol):
        node = builder.extract_node(f"""
        import gi

        gi.require_version("{namespace}", "{version}")
        from gi.repository import {namespace}
        {namespace}.{symbol}
        """)
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


class RequireVersionMatchTest(unittest.TestCase):
    """``_looks_like_require_version`` must only match gi's ``require_version``.

    A match triggers ``import gi`` and ``gi.require_version(...)`` at build time,
    so a false positive runs that side effect for unrelated source. This test
    needs no gi and asserts the predicate, not the side effect.
    """

    @staticmethod
    def _call(source: str) -> nodes.Call:
        call = builder.extract_node(source)
        assert isinstance(call, nodes.Call)
        return call

    def test_bare_name_from_gi_matches(self):
        self.assertTrue(
            _looks_like_require_version(
                self._call(
                    'from gi import require_version\nrequire_version("Gtk", "3.0")'
                )
            )
        )

    def test_gi_attribute_matches(self):
        self.assertTrue(
            _looks_like_require_version(
                self._call('import gi\ngi.require_version("Gtk", "3.0")')
            )
        )

    def test_local_function_does_not_match(self):
        self.assertFalse(
            _looks_like_require_version(
                self._call(
                    'def require_version(a, b): return None\nrequire_version("Gtk", "3.0")'
                )
            )
        )

    def test_undefined_name_does_not_match(self):
        self.assertFalse(
            _looks_like_require_version(self._call('require_version("Gtk", "3.0")'))
        )

    def test_other_module_attribute_does_not_match(self):
        self.assertFalse(
            _looks_like_require_version(
                self._call('import other\nother.require_version("Gtk", "3.0")')
            )
        )
