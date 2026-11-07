# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import importlib.machinery
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

try:
    import gi  # pylint: disable=unused-import

    HAS_GI = True
except ImportError:
    HAS_GI = False

from astroid import builder, nodes
from astroid.brain.brain_gi import (
    _gi_is_installed,
    _inspected_modules,
    _looks_like_require_version,
)
from astroid.exceptions import AstroidBuildingError
from astroid.manager import AstroidManager
from astroid.modutils import EXT_LIB_DIRS


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

    def test_star_import_from_gi_matches(self):
        self.assertTrue(
            _looks_like_require_version(
                self._call('from gi import *\nrequire_version("Gtk", "3.0")')
            )
        )

    def test_star_import_shadowed_by_local_does_not_match(self):
        self.assertFalse(
            _looks_like_require_version(
                self._call(
                    "from gi import *\n"
                    "def require_version(a, b): return None\n"
                    'require_version("Gtk", "3.0")'
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


class GiFromProjectTest(unittest.TestCase):
    """A ``gi`` package in the analysed project must not be imported."""

    def setUp(self) -> None:
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir)
        self.gi_dir = Path(tmpdir, "gi")
        (self.gi_dir / "repository").mkdir(parents=True)
        (self.gi_dir / "repository" / "__init__.py").touch()
        sys.path.insert(0, tmpdir)
        self.addCleanup(sys.path.remove, tmpdir)
        # Let the project package shadow an installed gi, as it does under pylint.
        patcher = mock.patch.dict(sys.modules)
        patcher.start()
        self.addCleanup(patcher.stop)
        for name in [n for n in sys.modules if n.split(".")[0] == "gi"]:
            del sys.modules[name]
        self.addCleanup(_inspected_modules.pop, "gi.repository.AstroidTest", None)

    def _add_init(self) -> None:
        (self.gi_dir / "__init__.py").touch()

    @staticmethod
    def _install_fake_gi() -> types.ModuleType:
        """Stand in for an installed gi without importing anything."""
        installed = types.ModuleType("gi")
        installed.__spec__ = importlib.machinery.ModuleSpec(
            "gi",
            None,
            origin=os.path.join(next(iter(EXT_LIB_DIRS)), "gi", "__init__.py"),
        )
        sys.modules["gi"] = installed
        return installed

    def test_failed_import_hook_does_not_import_project_gi(self) -> None:
        self._add_init()
        node = builder.extract_node("import gi.repository.AstroidTest")
        with self.assertRaises(AstroidBuildingError):
            node.do_import_module("gi.repository.AstroidTest")
        self.assertNotIn("gi", sys.modules)

    def test_require_version_does_not_import_project_gi(self) -> None:
        self._add_init()
        builder.extract_node('import gi\ngi.require_version("Gtk", "3.0")')
        self.assertNotIn("gi", sys.modules)

    def test_failed_import_hook_imports_installed_gi(self) -> None:
        self._install_fake_gi()
        node = builder.extract_node("import gi.repository.AstroidTest")
        with self.assertRaises(AstroidBuildingError):
            node.do_import_module("gi.repository.AstroidTest")
        self.assertIn("gi.repository.AstroidTest", _inspected_modules)

    def test_require_version_calls_installed_gi(self) -> None:
        require_version = self._install_fake_gi().require_version = mock.Mock()
        builder.extract_node('import gi\ngi.require_version("Gtk", "3.0")')
        require_version.assert_called_once_with("Gtk", "3.0")

    def test_namespace_package_is_not_installed(self) -> None:
        self.assertFalse(_gi_is_installed())

    def test_module_without_spec_is_not_installed(self) -> None:
        sys.modules["gi"] = types.ModuleType("gi")
        self.assertFalse(_gi_is_installed())

    def test_extension_allow_list_is_honoured(self) -> None:
        self._add_init()
        manager = AstroidManager()
        manager.extension_package_whitelist.add("gi")
        self.addCleanup(manager.extension_package_whitelist.discard, "gi")
        self.assertTrue(_gi_is_installed())
