# Copyright (c) 2006, 2009-2014 LOGILAB S.A. (Paris, FRANCE) <contact@logilab.fr>
# Copyright (c) 2013 AndroWiiid <androwiiid@gmail.com>
# Copyright (c) 2014-2020 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2014 Google, Inc.
# Copyright (c) 2015-2016 Ceridwen <ceridwenv@gmail.com>
# Copyright (c) 2017 Chris Philip <chrisp533@gmail.com>
# Copyright (c) 2017 Hugo <hugovk@users.noreply.github.com>
# Copyright (c) 2017 ioanatia <ioanatia@users.noreply.github.com>
# Copyright (c) 2018 Ville Skyttä <ville.skytta@iki.fi>
# Copyright (c) 2018 Bryce Guinta <bryce.paul.guinta@gmail.com>
# Copyright (c) 2019 Ashley Whetter <ashley@awhetter.co.uk>
# Copyright (c) 2019 Hugo van Kemenade <hugovk@users.noreply.github.com>
# Copyright (c) 2020-2021 hippo91 <guillaume.peillex@gmail.com>
# Copyright (c) 2020 David Gilman <davidgilman1@gmail.com>
# Copyright (c) 2020 Anubhav <35621759+anubh-v@users.noreply.github.com>
# Copyright (c) 2021 Pierre Sassoulas <pierre.sassoulas@gmail.com>
# Copyright (c) 2021 Tushar Sadhwani <86737547+tushar-deepsource@users.noreply.github.com>
# Copyright (c) 2021 grayjk <grayjk@gmail.com>
# Copyright (c) 2021 Marc Mueller <30130371+cdce8p@users.noreply.github.com>
# Copyright (c) 2021 Andrew Haigh <hello@nelf.in>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE

import os
import platform
import site
import sys
import time
import unittest
from contextlib import contextmanager
from typing import Iterator

import pkg_resources

import astroid
from astroid import manager, test_utils
from astroid.exceptions import AstroidBuildingError, AstroidImportError

from . import resources


def _get_file_from_object(obj) -> str:
    if platform.python_implementation() == "Jython":
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
        pkg_resources._namespace_packages["foogle"] = []

        try:
            module = self.manager.ast_from_module_name("foogle.fax")
            submodule = next(module.igetattr("a"))
            value = next(submodule.igetattr("x"))
            self.assertIsInstance(value, astroid.Const)
            with self.assertRaises(AstroidImportError):
                self.manager.ast_from_module_name("foogle.moogle")
        finally:
            del pkg_resources._namespace_packages["foogle"]
            sys.modules.pop("foogle")

    def test_nested_namespace_import(self) -> None:
        pth = "foogle_fax-0.12.5-py2.7-nspkg.pth"
        site.addpackage(resources.RESOURCE_PATH, pth, [])
        pkg_resources._namespace_packages["foogle"] = ["foogle.crank"]
        pkg_resources._namespace_packages["foogle.crank"] = []
        try:
            self.manager.ast_from_module_name("foogle.crank")
        finally:
            del pkg_resources._namespace_packages["foogle"]
            sys.modules.pop("foogle")

    def test_namespace_and_file_mismatch(self) -> None:
        filepath = unittest.__file__
        ast = self.manager.ast_from_file(filepath)
        self.assertEqual(ast.name, "unittest")
        pth = "foogle_fax-0.12.5-py2.7-nspkg.pth"
        site.addpackage(resources.RESOURCE_PATH, pth, [])
        pkg_resources._namespace_packages["foogle"] = []
        try:
            with self.assertRaises(AstroidImportError):
                self.manager.ast_from_module_name("unittest.foogle.fax")
        finally:
            del pkg_resources._namespace_packages["foogle"]
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


class BorgAstroidManagerTC(unittest.TestCase):
    def test_borg(self) -> None:
        """test that the AstroidManager is really a borg, i.e. that two different
        instances has same cache"""
        first_manager = manager.AstroidManager()
        built = first_manager.ast_from_module_name("builtins")

        second_manager = manager.AstroidManager()
        second_built = second_manager.ast_from_module_name("builtins")
        self.assertIs(built, second_built)


if __name__ == "__main__":
    unittest.main()
