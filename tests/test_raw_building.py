"""
'tests.testdata.python3.data.fake_module_with_warnings' and
'tests.testdata.python3.data.fake_module_with_warnings' are fake modules
to simulate issues in unittest below
"""

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import _io
import logging
import os
import sys
import types
import unittest
from typing import Any
from unittest import mock

import pytest

import tests.testdata.python3.data.fake_module_with_broken_getattr as fm_getattr
import tests.testdata.python3.data.fake_module_with_warnings as fm
from astroid.builder import AstroidBuilder
from astroid.const import IS_PYPY, PY312_PLUS
from astroid.raw_building import (
    attach_dummy_node,
    build_class,
    build_from_import,
    build_function,
    build_module,
)


class RawBuildingTC(unittest.TestCase):
    def test_attach_dummy_node(self) -> None:
        node = build_module("MyModule")
        attach_dummy_node(node, "DummyNode")
        self.assertEqual(1, len(list(node.get_children())))

    def test_build_module(self) -> None:
        node = build_module("MyModule")
        self.assertEqual(node.name, "MyModule")
        self.assertEqual(node.pure_python, False)
        self.assertEqual(node.package, False)
        self.assertEqual(node.parent, None)

    def test_build_class(self) -> None:
        node = build_class("MyClass")
        self.assertEqual(node.name, "MyClass")
        self.assertEqual(node.doc_node, None)

    def test_build_function(self) -> None:
        node = build_function("MyFunction")
        self.assertEqual(node.name, "MyFunction")
        self.assertEqual(node.doc_node, None)

    def test_build_function_args(self) -> None:
        args = ["myArgs1", "myArgs2"]
        node = build_function("MyFunction", args)
        self.assertEqual("myArgs1", node.args.args[0].name)
        self.assertEqual("myArgs2", node.args.args[1].name)
        self.assertEqual(2, len(node.args.args))

    def test_build_function_defaults(self) -> None:
        defaults = ["defaults1", "defaults2"]
        node = build_function(name="MyFunction", args=None, defaults=defaults)
        self.assertEqual(2, len(node.args.defaults))

    def test_build_function_posonlyargs(self) -> None:
        node = build_function(name="MyFunction", posonlyargs=["a", "b"])
        self.assertEqual(2, len(node.args.posonlyargs))

    def test_build_function_kwonlyargs(self) -> None:
        node = build_function(name="MyFunction", kwonlyargs=["a", "b"])
        assert len(node.args.kwonlyargs) == 2
        assert node.args.kwonlyargs[0].name == "a"
        assert node.args.kwonlyargs[1].name == "b"

    def test_build_from_import(self) -> None:
        names = ["exceptions, inference, inspector"]
        node = build_from_import("astroid", names)
        self.assertEqual(len(names), len(node.names))

    @unittest.skipIf(IS_PYPY, "Only affects CPython")
    def test_io_is__io(self):
        # _io module calls itself io before Python 3.12. This leads
        # to cyclic dependencies when astroid tries to resolve
        # what io.BufferedReader is. The code that handles this
        # is in astroid.raw_building.imported_member, which verifies
        # the true name of the module.
        builder = AstroidBuilder()
        module = builder.inspect_build(_io)
        buffered_reader = module.getattr("BufferedReader")[0]
        expected = "_io" if PY312_PLUS else "io"
        self.assertEqual(buffered_reader.root().name, expected)

    def test_build_function_deepinspect_deprecation(self) -> None:
        # Tests https://github.com/pylint-dev/astroid/issues/1717
        # When astroid deep inspection of modules raises
        # attribute errors when getting all attributes
        # Create a mock module to simulate a Cython module
        m = types.ModuleType("test")

        # Attach a mock of pandas with the same behavior
        m.pd = fm

        # This should not raise an exception
        AstroidBuilder().module_build(m, "test")

    def test_module_object_with_broken_getattr(self) -> None:
        # Tests https://github.com/pylint-dev/astroid/issues/1958
        # When astroid deep inspection of modules raises
        # errors when using hasattr().

        # This should not raise an exception
        AstroidBuilder().inspect_build(fm_getattr, "test")


@pytest.mark.skipif(
    "posix" not in sys.builtin_module_names, reason="Platform doesn't support posix"
)
def test_build_module_getattr_catch_output(
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Catch stdout and stderr in module __getattr__ calls when building a module.

    Usually raised by DeprecationWarning or FutureWarning.
    """
    caplog.set_level(logging.INFO)
    original_sys = sys.modules
    original_module = sys.modules["posix"]
    expected_out = "INFO (TEST): Welcome to posix!"
    expected_err = "WARNING (TEST): Monkey-patched version of posix - module getattr"

    class CustomGetattr:
        def __getattr__(self, name: str) -> Any:
            print(f"{expected_out}")
            print(expected_err, file=sys.stderr)
            return getattr(original_module, name)

    def mocked_sys_modules_getitem(name: str) -> types.ModuleType | CustomGetattr:
        if name != "posix":
            return original_sys[name]
        return CustomGetattr()

    with mock.patch("astroid.raw_building.sys.modules") as sys_mock:
        sys_mock.__getitem__.side_effect = mocked_sys_modules_getitem
        builder = AstroidBuilder()
        builder.inspect_build(os)

    out, err = capsys.readouterr()
    assert expected_out in caplog.text
    assert expected_err in caplog.text
    assert not out
    assert not err
