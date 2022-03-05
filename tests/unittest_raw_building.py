# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

import unittest

import _io
import pytest

from astroid.builder import AstroidBuilder
from astroid.const import IS_PYPY
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
        with pytest.warns(DeprecationWarning) as records:
            self.assertEqual(node.doc, None)
            assert len(records) == 1
        self.assertEqual(node.doc_node, None)

    def test_build_function(self) -> None:
        node = build_function("MyFunction")
        self.assertEqual(node.name, "MyFunction")
        with pytest.warns(DeprecationWarning) as records:
            self.assertEqual(node.doc, None)
            assert len(records) == 1
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
        # _io module calls itself io. This leads
        # to cyclic dependencies when astroid tries to resolve
        # what io.BufferedReader is. The code that handles this
        # is in astroid.raw_building.imported_member, which verifies
        # the true name of the module.
        builder = AstroidBuilder()
        module = builder.inspect_build(_io)
        buffered_reader = module.getattr("BufferedReader")[0]
        self.assertEqual(buffered_reader.root().name, "io")


if __name__ == "__main__":
    unittest.main()
