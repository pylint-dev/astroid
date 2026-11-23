# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import unittest
from unittest.mock import patch

import pytest

from astroid import builder, nodes, util
from astroid.exceptions import AttributeInferenceError


class NamedTupleTest(unittest.TestCase):
    def test_namedtuple_base(self) -> None:
        klass = builder.extract_node("""
        from collections import namedtuple

        class X(namedtuple("X", ["a", "b", "c"])):
           pass
        """)
        assert isinstance(klass, nodes.ClassDef)
        self.assertEqual(
            [ancestor.name for ancestor in klass.ancestors()], ["X", "tuple", "object"]
        )
        # See: https://github.com/pylint-dev/pylint/issues/5982
        self.assertNotIn("X", klass.locals)
        for ancestor in klass.ancestors():
            self.assertFalse(ancestor.parent is None)

    def test_namedtuple_inference(self) -> None:
        klass = builder.extract_node("""
        from collections import namedtuple

        name = "X"
        fields = ["a", "b", "c"]
        class X(namedtuple(name, fields)):
           pass
        """)
        assert isinstance(klass, nodes.ClassDef)
        base = next(base for base in klass.ancestors() if base.name == "X")
        self.assertSetEqual({"a", "b", "c"}, set(base.instance_attrs))

    def test_namedtuple_advanced_inference(self) -> None:
        # urlparse return an object of class ParseResult, which has a
        # namedtuple call and a mixin as base classes
        result = builder.extract_node("""
        from urllib.parse import urlparse

        result = __(urlparse('gopher://'))
        """)
        instance = next(result.infer())
        self.assertGreaterEqual(len(instance.getattr("scheme")), 1)
        self.assertGreaterEqual(len(instance.getattr("port")), 1)
        with self.assertRaises(AttributeInferenceError):
            instance.getattr("foo")
        self.assertGreaterEqual(len(instance.getattr("geturl")), 1)
        self.assertEqual(instance.name, "ParseResult")

    def test_namedtuple_instance_attrs(self) -> None:
        result = builder.extract_node("""
        from collections import namedtuple
        namedtuple('a', 'a b c')(1, 2, 3) #@
        """)
        inferred = next(result.infer())
        for name, attr in inferred.instance_attrs.items():
            self.assertEqual(attr[0].attrname, name)


def _unresolved_namedtuple_factory(factory):
    """Make only the ``collections.namedtuple`` lookup of the brain fail."""
    real_safe_infer = util.safe_infer

    def fake_safe_infer(node, *args, **kwargs):
        if isinstance(node, nodes.Attribute) and node.attrname == "namedtuple":
            return factory
        return real_safe_infer(node, *args, **kwargs)

    return patch(
        "astroid.brain.brain_namedtuple_enum.util.safe_infer",
        side_effect=fake_safe_infer,
    )


@pytest.mark.parametrize(
    "factory", [None, util.Uninferable], ids=["none", "uninferable"]
)
def test_namedtuple_unresolved_factory_keeps_fields(factory) -> None:
    """Without the factory, ``rename=`` falls back to ``False``."""
    node = builder.extract_node("""
    from collections import namedtuple
    namedtuple('Client', 'value')
    """)
    with _unresolved_namedtuple_factory(factory):
        inferred = next(node.infer())
    assert isinstance(inferred, nodes.ClassDef)
    assert list(inferred.instance_attrs) == ["value"]
    assert inferred.getattr("_replace")


@pytest.mark.parametrize(
    "factory", [None, util.Uninferable], ids=["none", "uninferable"]
)
def test_typing_namedtuple_unresolved_factory_keeps_fields(factory) -> None:
    node = builder.extract_node("""
    import typing

    class Client(typing.NamedTuple):
        value: int

    Client
    """)
    with _unresolved_namedtuple_factory(factory):
        inferred = next(node.infer())
    assert isinstance(inferred, nodes.ClassDef)
    assert inferred.name == "Client"
    assert list(inferred.instance_attrs) == ["value"]
    assert inferred.getattr("_replace")
