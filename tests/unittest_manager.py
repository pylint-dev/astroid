# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

import os
import site
import sys
import time
import unittest
from collections.abc import Iterator
from contextlib import contextmanager

import astroid
from astroid import manager, test_utils
from astroid.const import IS_JYTHON
from astroid.exceptions import AstroidBuildingError, AstroidImportError
from astroid.interpreter._import import util
from astroid.modutils import is_standard_module
from astroid.nodes import Const
from astroid.nodes.scoped_nodes import ClassDef

from . import resources


def _get_file_from_object(obj) -> str:
    if IS_JYTHON:
        return obj.__file__.split("$py.class")[0] + ".py"
    return obj.__file__


class AstroidManagerTest(
    resources.SysPathSetup, resources.AstroidCacheSetupMixin, unittest.TestCase
):
    def setUp(self) -> None:
        super().setUp()
        self.manager = test_utils.brainless_manager()

    def test_ast_from_file(self) -> None:
        filepath = unittest.__file__
        ast = self.manager.ast_from_file(filepath)
        self.assertEqual(ast.name, "unittest")
        self.assertIn("unittest", self.manager.astroid_cache)

    def test_ast_from_file_cache(self) -> None:
        filepath = unittest.__file__
        self.manager.ast_from_file(filepath)
        ast = self.manager.ast_from_file("unhandledName", "unittest")
        self.assertEqual(ast.name, "unittest")
        self.assertIn("unittest", self.manager.astroid_cache)

    def test_ast_from_file_astro_builder(self) -> None:
        filepath = unittest.__file__
        ast = self.manager.ast_from_file(filepath, None, True, True)
        self.assertEqual(ast.name, "unittest")
        self.assertIn("unittest", self.manager.astroid_cache)

    def test_ast_from_file_name_astro_builder_exception(self) -> None:
        self.assertRaises(
            AstroidBuildingError, self.manager.ast_from_file, "unhandledName"
        )

    def test_ast_from_string(self) -> None:
        filepath = unittest.__file__
        dirname = os.path.dirname(filepath)
        modname = os.path.basename(dirname)
        with open(filepath, encoding="utf-8") as file:
            data = file.read()
            ast = self.manager.ast_from_string(data, modname, filepath)
            self.assertEqual(ast.name, "unittest")
            self.assertEqual(ast.file, filepath)
            self.assertIn("unittest", self.manager.astroid_cache)

    def test_do_not_expose_main(self) -> None:
        obj = self.manager.ast_from_module_name("__main__")
        self.assertEqual(obj.name, "__main__")
        self.assertEqual(obj.items(), [])

    def test_ast_from_module_name(self) -> None:
        ast = self.manager.ast_from_module_name("unittest")
        self.assertEqual(ast.name, "unittest")
        self.assertIn("unittest", self.manager.astroid_cache)

    def test_ast_from_module_name_not_python_source(self) -> None:
        ast = self.manager.ast_from_module_name("time")
        self.assertEqual(ast.name, "time")
        self.assertIn("time", self.manager.astroid_cache)
        self.assertEqual(ast.pure_python, False)

    def test_ast_from_module_name_astro_builder_exception(self) -> None:
        self.assertRaises(
            AstroidBuildingError,
            self.manager.ast_from_module_name,
            "unhandledModule",
        )

    def _test_ast_from_old_namespace_package_protocol(self, root: str) -> None:
        origpath = sys.path[:]
        paths = [resources.find(f"data/path_{root}_{index}") for index in range(1, 4)]
        sys.path.extend(paths)
        try:
            for name in ("foo", "bar", "baz"):
                module = self.manager.ast_from_module_name("package." + name)
                self.assertIsInstance(module, astroid.Module)
        finally:
            sys.path = origpath

    def test_ast_from_namespace_pkgutil(self) -> None:
        self._test_ast_from_old_namespace_package_protocol("pkgutil")

    def test_ast_from_namespace_pkg_resources(self) -> None:
        self._test_ast_from_old_namespace_package_protocol("pkg_resources")

    def test_identify_old_namespace_package_protocol(self) -> None:
        # Like the above cases, this package follows the old namespace package protocol
        # astroid currently assumes such packages are in sys.modules, so import it
        # pylint: disable-next=import-outside-toplevel
        import tests.testdata.python3.data.path_pkg_resources_1.package.foo as _  # noqa

        self.assertTrue(
            util.is_namespace("tests.testdata.python3.data.path_pkg_resources_1")
        )

    def test_submodule_homonym_with_non_module(self) -> None:
        self.assertFalse(
            util.is_namespace("tests.testdata.python3.data.parent_of_homonym.doc")
        )

    def test_module_is_not_namespace(self) -> None:
        self.assertFalse(util.is_namespace("tests.testdata.python3.data.all"))
        self.assertFalse(util.is_namespace("__main__"))
        self.assertFalse(util.is_namespace("importlib._bootstrap"))

    def test_module_unexpectedly_missing_spec(self) -> None:
        astroid_module = sys.modules["astroid"]
        original_spec = astroid_module.__spec__
        del astroid_module.__spec__
        try:
            self.assertFalse(util.is_namespace("astroid"))
        finally:
            astroid_module.__spec__ = original_spec

    def test_implicit_namespace_package(self) -> None:
        data_dir = os.path.dirname(resources.find("data/namespace_pep_420"))
        contribute = os.path.join(data_dir, "contribute_to_namespace")
        for value in (data_dir, contribute):
            sys.path.insert(0, value)

        try:
            module = self.manager.ast_from_module_name("namespace_pep_420.module")
            self.assertIsInstance(module, astroid.Module)
            self.assertEqual(module.name, "namespace_pep_420.module")
            var = next(module.igetattr("var"))
            self.assertIsInstance(var, astroid.Const)
            self.assertEqual(var.value, 42)
        finally:
            for _ in range(2):
                sys.path.pop(0)

    def test_namespace_package_pth_support(self) -> None:
        pth = "foogle_fax-0.12.5-py2.7-nspkg.pth"
        site.addpackage(resources.RESOURCE_PATH, pth, [])

        try:
            module = self.manager.ast_from_module_name("foogle.fax")
            submodule = next(module.igetattr("a"))
            value = next(submodule.igetattr("x"))
            self.assertIsInstance(value, astroid.Const)
            with self.assertRaises(AstroidImportError):
                self.manager.ast_from_module_name("foogle.moogle")
        finally:
            sys.modules.pop("foogle")

    def test_nested_namespace_import(self) -> None:
        pth = "foogle_fax-0.12.5-py2.7-nspkg.pth"
        site.addpackage(resources.RESOURCE_PATH, pth, [])
        try:
            self.manager.ast_from_module_name("foogle.crank")
        finally:
            sys.modules.pop("foogle")

    def test_namespace_and_file_mismatch(self) -> None:
        filepath = unittest.__file__
        ast = self.manager.ast_from_file(filepath)
        self.assertEqual(ast.name, "unittest")
        pth = "foogle_fax-0.12.5-py2.7-nspkg.pth"
        site.addpackage(resources.RESOURCE_PATH, pth, [])
        try:
            with self.assertRaises(AstroidImportError):
                self.manager.ast_from_module_name("unittest.foogle.fax")
        finally:
            sys.modules.pop("foogle")

    def _test_ast_from_zip(self, archive: str) -> None:
        sys.modules.pop("mypypa", None)
        archive_path = resources.find(archive)
        sys.path.insert(0, archive_path)
        module = self.manager.ast_from_module_name("mypypa")
        self.assertEqual(module.name, "mypypa")
        end = os.path.join(archive, "mypypa")
        self.assertTrue(
            module.file.endswith(end), f"{module.file} doesn't endswith {end}"
        )

    @contextmanager
    def _restore_package_cache(self) -> Iterator:
        orig_path = sys.path[:]
        orig_pathcache = sys.path_importer_cache.copy()
        orig_modcache = self.manager.astroid_cache.copy()
        orig_modfilecache = self.manager._mod_file_cache.copy()
        orig_importhooks = self.manager._failed_import_hooks[:]
        yield
        self.manager._failed_import_hooks = orig_importhooks
        self.manager._mod_file_cache = orig_modfilecache
        self.manager.astroid_cache = orig_modcache
        sys.path_importer_cache = orig_pathcache
        sys.path = orig_path

    def test_ast_from_module_name_egg(self) -> None:
        with self._restore_package_cache():
            self._test_ast_from_zip(
                os.path.sep.join(["data", os.path.normcase("MyPyPa-0.1.0-py2.5.egg")])
            )

    def test_ast_from_module_name_zip(self) -> None:
        with self._restore_package_cache():
            self._test_ast_from_zip(
                os.path.sep.join(["data", os.path.normcase("MyPyPa-0.1.0-py2.5.zip")])
            )

    def test_ast_from_module_name_pyz(self) -> None:
        try:
            linked_file_name = os.path.join(
                resources.RESOURCE_PATH, "MyPyPa-0.1.0-py2.5.pyz"
            )
            os.symlink(
                os.path.join(resources.RESOURCE_PATH, "MyPyPa-0.1.0-py2.5.zip"),
                linked_file_name,
            )

            with self._restore_package_cache():
                self._test_ast_from_zip(linked_file_name)
        finally:
            os.remove(linked_file_name)

    def test_zip_import_data(self) -> None:
        """check if zip_import_data works"""
        with self._restore_package_cache():
            filepath = resources.find("data/MyPyPa-0.1.0-py2.5.zip/mypypa")
            ast = self.manager.zip_import_data(filepath)
            self.assertEqual(ast.name, "mypypa")

    def test_zip_import_data_without_zipimport(self) -> None:
        """check if zip_import_data return None without zipimport"""
        self.assertEqual(self.manager.zip_import_data("path"), None)

    def test_file_from_module(self) -> None:
        """check if the unittest filepath is equals to the result of the method"""
        self.assertEqual(
            _get_file_from_object(unittest),
            self.manager.file_from_module_name("unittest", None).location,
        )

    def test_file_from_module_name_astro_building_exception(self) -> None:
        """check if the method raises an exception with a wrong module name"""
        self.assertRaises(
            AstroidBuildingError,
            self.manager.file_from_module_name,
            "unhandledModule",
            None,
        )

    def test_ast_from_module(self) -> None:
        ast = self.manager.ast_from_module(unittest)
        self.assertEqual(ast.pure_python, True)
        ast = self.manager.ast_from_module(time)
        self.assertEqual(ast.pure_python, False)

    def test_ast_from_module_cache(self) -> None:
        """check if the module is in the cache manager"""
        ast = self.manager.ast_from_module(unittest)
        self.assertEqual(ast.name, "unittest")
        self.assertIn("unittest", self.manager.astroid_cache)

    def test_ast_from_class(self) -> None:
        ast = self.manager.ast_from_class(int)
        self.assertEqual(ast.name, "int")
        self.assertEqual(ast.parent.frame().name, "builtins")
        self.assertEqual(ast.parent.frame(future=True).name, "builtins")

        ast = self.manager.ast_from_class(object)
        self.assertEqual(ast.name, "object")
        self.assertEqual(ast.parent.frame().name, "builtins")
        self.assertEqual(ast.parent.frame(future=True).name, "builtins")
        self.assertIn("__setattr__", ast)

    def test_ast_from_class_with_module(self) -> None:
        """check if the method works with the module name"""
        ast = self.manager.ast_from_class(int, int.__module__)
        self.assertEqual(ast.name, "int")
        self.assertEqual(ast.parent.frame().name, "builtins")
        self.assertEqual(ast.parent.frame(future=True).name, "builtins")

        ast = self.manager.ast_from_class(object, object.__module__)
        self.assertEqual(ast.name, "object")
        self.assertEqual(ast.parent.frame().name, "builtins")
        self.assertEqual(ast.parent.frame(future=True).name, "builtins")
        self.assertIn("__setattr__", ast)

    def test_ast_from_class_attr_error(self) -> None:
        """give a wrong class at the ast_from_class method"""
        self.assertRaises(AstroidBuildingError, self.manager.ast_from_class, None)

    def test_failed_import_hooks(self) -> None:
        def hook(modname: str):
            if modname == "foo.bar":
                return unittest

            raise AstroidBuildingError()

        with self.assertRaises(AstroidBuildingError):
            self.manager.ast_from_module_name("foo.bar")

        with self._restore_package_cache():
            self.manager.register_failed_import_hook(hook)
            self.assertEqual(unittest, self.manager.ast_from_module_name("foo.bar"))
            with self.assertRaises(AstroidBuildingError):
                self.manager.ast_from_module_name("foo.bar.baz")

    def test_same_name_import_module(self) -> None:
        """Test inference of an import statement with the same name as the module.

        See https://github.com/PyCQA/pylint/issues/5151.
        """
        math_file = resources.find("data/import_conflicting_names/math.py")
        module = self.manager.ast_from_file(math_file)

        # Change the cache key and module name to mimic importing the test file
        # from the root/top level. This creates a clash between math.py and stdlib math.
        self.manager.astroid_cache["math"] = self.manager.astroid_cache.pop(module.name)
        module.name = "math"

        # Infer the 'import math' statement
        stdlib_math = next(module.body[1].value.args[0].infer())
        assert self.manager.astroid_cache["math"] != stdlib_math


class BorgAstroidManagerTC(unittest.TestCase):
    def test_borg(self) -> None:
        """test that the AstroidManager is really a borg, i.e. that two different
        instances has same cache"""
        first_manager = manager.AstroidManager()
        built = first_manager.ast_from_module_name("builtins")

        second_manager = manager.AstroidManager()
        second_built = second_manager.ast_from_module_name("builtins")
        self.assertIs(built, second_built)


class ClearCacheTest(unittest.TestCase):
    def test_clear_cache_clears_other_lru_caches(self) -> None:
        lrus = (
            astroid.nodes.node_classes.LookupMixIn.lookup,
            astroid.modutils._cache_normalize_path_,
            util.is_namespace,
            astroid.interpreter.objectmodel.ObjectModel.attributes,
        )

        # Get a baseline for the size of the cache after simply calling bootstrap()
        baseline_cache_infos = [lru.cache_info() for lru in lrus]

        # Generate some hits and misses
        ClassDef().lookup("garbage")
        is_standard_module("unittest", std_path=["garbage_path"])
        util.is_namespace("unittest")
        astroid.interpreter.objectmodel.ObjectModel().attributes()

        # Did the hits or misses actually happen?
        incremented_cache_infos = [lru.cache_info() for lru in lrus]
        for incremented_cache, baseline_cache in zip(
            incremented_cache_infos, baseline_cache_infos
        ):
            with self.subTest(incremented_cache=incremented_cache):
                self.assertGreater(
                    incremented_cache.hits + incremented_cache.misses,
                    baseline_cache.hits + baseline_cache.misses,
                )

        astroid.MANAGER.clear_cache()  # also calls bootstrap()

        # The cache sizes are now as low or lower than the original baseline
        cleared_cache_infos = [lru.cache_info() for lru in lrus]
        for cleared_cache, baseline_cache in zip(
            cleared_cache_infos, baseline_cache_infos
        ):
            with self.subTest(cleared_cache=cleared_cache):
                # less equal because the "baseline" might have had multiple calls to bootstrap()
                self.assertLessEqual(cleared_cache.currsize, baseline_cache.currsize)

    def test_brain_plugins_reloaded_after_clearing_cache(self) -> None:
        astroid.MANAGER.clear_cache()
        format_call = astroid.extract_node("''.format()")
        inferred = next(format_call.infer())
        self.assertIsInstance(inferred, Const)

    def test_builtins_inference_after_clearing_cache(self) -> None:
        astroid.MANAGER.clear_cache()
        isinstance_call = astroid.extract_node("isinstance(1, int)")
        inferred = next(isinstance_call.infer())
        self.assertIs(inferred.value, True)

    def test_builtins_inference_after_clearing_cache_manually(self) -> None:
        # Not recommended to manipulate this, so we detect it and call clear_cache() instead
        astroid.MANAGER.brain["astroid_cache"].clear()
        isinstance_call = astroid.extract_node("isinstance(1, int)")
        inferred = next(isinstance_call.infer())
        self.assertIs(inferred.value, True)


if __name__ == "__main__":
    unittest.main()
