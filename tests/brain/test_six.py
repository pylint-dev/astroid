# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import unittest
from typing import Any

import astroid
from astroid import MANAGER, builder, nodes
from astroid.nodes.scoped_nodes import ClassDef

try:
    import six  # type: ignore[import]  # pylint: disable=unused-import

    HAS_SIX = True
except ImportError:
    HAS_SIX = False


@unittest.skipUnless(HAS_SIX, "These tests require the six library")
class SixBrainTest(unittest.TestCase):
    def test_attribute_access(self) -> None:
        ast_nodes = builder.extract_node(
            """
        import six
        six.moves.http_client #@
        six.moves.urllib_parse #@
        six.moves.urllib_error #@
        six.moves.urllib.request #@
        from six.moves import StringIO
        StringIO #@
        """
        )
        assert isinstance(ast_nodes, list)
        http_client = next(ast_nodes[0].infer())
        self.assertIsInstance(http_client, nodes.Module)
        self.assertEqual(http_client.name, "http.client")

        urllib_parse = next(ast_nodes[1].infer())
        self.assertIsInstance(urllib_parse, nodes.Module)
        self.assertEqual(urllib_parse.name, "urllib.parse")
        urljoin = next(urllib_parse.igetattr("urljoin"))
        urlencode = next(urllib_parse.igetattr("urlencode"))
        self.assertIsInstance(urljoin, nodes.FunctionDef)
        self.assertEqual(urljoin.qname(), "urllib.parse.urljoin")
        self.assertIsInstance(urlencode, nodes.FunctionDef)
        self.assertEqual(urlencode.qname(), "urllib.parse.urlencode")

        urllib_error = next(ast_nodes[2].infer())
        self.assertIsInstance(urllib_error, nodes.Module)
        self.assertEqual(urllib_error.name, "urllib.error")
        urlerror = next(urllib_error.igetattr("URLError"))
        self.assertIsInstance(urlerror, nodes.ClassDef)
        content_too_short = next(urllib_error.igetattr("ContentTooShortError"))
        self.assertIsInstance(content_too_short, nodes.ClassDef)

        urllib_request = next(ast_nodes[3].infer())
        self.assertIsInstance(urllib_request, nodes.Module)
        self.assertEqual(urllib_request.name, "urllib.request")
        urlopen = next(urllib_request.igetattr("urlopen"))
        urlretrieve = next(urllib_request.igetattr("urlretrieve"))
        self.assertIsInstance(urlopen, nodes.FunctionDef)
        self.assertEqual(urlopen.qname(), "urllib.request.urlopen")
        self.assertIsInstance(urlretrieve, nodes.FunctionDef)
        self.assertEqual(urlretrieve.qname(), "urllib.request.urlretrieve")

        StringIO = next(ast_nodes[4].infer())
        self.assertIsInstance(StringIO, nodes.ClassDef)
        self.assertEqual(StringIO.qname(), "_io.StringIO")
        self.assertTrue(StringIO.callable())

    def test_attribute_access_with_six_moves_imported(self) -> None:
        astroid.MANAGER.clear_cache()
        astroid.MANAGER._mod_file_cache.clear()
        import six.moves  # type: ignore[import]  # pylint: disable=import-outside-toplevel,unused-import,redefined-outer-name

        self.test_attribute_access()

    def test_from_imports(self) -> None:
        ast_node = builder.extract_node(
            """
        from six.moves import http_client
        http_client.HTTPSConnection #@
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, nodes.ClassDef)
        qname = "http.client.HTTPSConnection"
        self.assertEqual(inferred.qname(), qname)

    def test_from_submodule_imports(self) -> None:
        """Make sure ulrlib submodules can be imported from

        See pylint-dev/pylint#1640 for relevant issue
        """
        ast_node = builder.extract_node(
            """
        from six.moves.urllib.parse import urlparse
        urlparse #@
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, nodes.FunctionDef)

    def test_with_metaclass_subclasses_inheritance(self) -> None:
        ast_node = builder.extract_node(
            """
        class A(type):
            def test(cls):
                return cls

        class C:
            pass

        import six
        class B(six.with_metaclass(A, C)):
            pass

        B #@
        """
        )
        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, nodes.ClassDef)
        self.assertEqual(inferred.name, "B")
        self.assertIsInstance(inferred.bases[0], nodes.Call)
        ancestors = tuple(inferred.ancestors())
        self.assertIsInstance(ancestors[0], nodes.ClassDef)
        self.assertEqual(ancestors[0].name, "C")
        self.assertIsInstance(ancestors[1], nodes.ClassDef)
        self.assertEqual(ancestors[1].name, "object")

    @staticmethod
    def test_six_with_metaclass_enum_ancestor() -> None:
        code = """
        import six
        from enum import Enum, EnumMeta

        class FooMeta(EnumMeta):
            pass

        class Foo(six.with_metaclass(FooMeta, Enum)):  #@
            bar = 1
        """
        klass = astroid.extract_node(code)
        assert next(klass.ancestors()).name == "Enum"

    def test_six_with_metaclass_with_additional_transform(self) -> None:
        def transform_class(cls: Any) -> ClassDef:
            if cls.name == "A":
                cls._test_transform = 314
            return cls

        MANAGER.register_transform(nodes.ClassDef, transform_class)
        try:
            ast_node = builder.extract_node(
                """
                import six
                class A(six.with_metaclass(type, object)):
                    pass

                A #@
            """
            )
            inferred = next(ast_node.infer())
            assert getattr(inferred, "_test_transform", None) == 314
        finally:
            MANAGER.unregister_transform(nodes.ClassDef, transform_class)
