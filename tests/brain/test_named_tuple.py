# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import unittest

import astroid
from astroid import builder, nodes, util
from astroid.exceptions import AttributeInferenceError


class NamedTupleTest(unittest.TestCase):
    def test_namedtuple_base(self) -> None:
        klass = builder.extract_node(
            """
        from collections import namedtuple

        class X(namedtuple("X", ["a", "b", "c"])):
           pass
        """
        )
        assert isinstance(klass, nodes.ClassDef)
        self.assertEqual(
            [anc.name for anc in klass.ancestors()], ["X", "tuple", "object"]
        )
        # See: https://github.com/pylint-dev/pylint/issues/5982
        self.assertNotIn("X", klass.locals)
        for anc in klass.ancestors():
            self.assertFalse(anc.parent is None)

    def test_namedtuple_inference(self) -> None:
        klass = builder.extract_node(
            """
        from collections import namedtuple

        name = "X"
        fields = ["a", "b", "c"]
        class X(namedtuple(name, fields)):
           pass
        """
        )
        assert isinstance(klass, nodes.ClassDef)
        base = next(base for base in klass.ancestors() if base.name == "X")
        self.assertSetEqual({"a", "b", "c"}, set(base.instance_attrs))

    def test_namedtuple_inference_failure(self) -> None:
        klass = builder.extract_node(
            """
        from collections import namedtuple

        def foo(fields):
           return __(namedtuple("foo", fields))
        """
        )
        self.assertIs(util.Uninferable, next(klass.infer()))

    def test_namedtuple_advanced_inference(self) -> None:
        # urlparse return an object of class ParseResult, which has a
        # namedtuple call and a mixin as base classes
        result = builder.extract_node(
            """
        from urllib.parse import urlparse

        result = __(urlparse('gopher://'))
        """
        )
        instance = next(result.infer())
        self.assertGreaterEqual(len(instance.getattr("scheme")), 1)
        self.assertGreaterEqual(len(instance.getattr("port")), 1)
        with self.assertRaises(AttributeInferenceError):
            instance.getattr("foo")
        self.assertGreaterEqual(len(instance.getattr("geturl")), 1)
        self.assertEqual(instance.name, "ParseResult")

    def test_namedtuple_instance_attrs(self) -> None:
        result = builder.extract_node(
            """
        from collections import namedtuple
        namedtuple('a', 'a b c')(1, 2, 3) #@
        """
        )
        inferred = next(result.infer())
        for name, attr in inferred.instance_attrs.items():
            self.assertEqual(attr[0].attrname, name)

    def test_namedtuple_uninferable_fields(self) -> None:
        node = builder.extract_node(
            """
        x = [A] * 2
        from collections import namedtuple
        l = namedtuple('a', x)
        l(1)
        """
        )
        inferred = next(node.infer())
        self.assertIs(util.Uninferable, inferred)

    def test_namedtuple_access_class_fields(self) -> None:
        node = builder.extract_node(
            """
        from collections import namedtuple
        Tuple = namedtuple("Tuple", "field other")
        Tuple #@
        """
        )
        inferred = next(node.infer())
        self.assertIn("field", inferred.locals)
        self.assertIn("other", inferred.locals)

    def test_namedtuple_rename_keywords(self) -> None:
        node = builder.extract_node(
            """
        from collections import namedtuple
        Tuple = namedtuple("Tuple", "abc def", rename=True)
        Tuple #@
        """
        )
        inferred = next(node.infer())
        self.assertIn("abc", inferred.locals)
        self.assertIn("_1", inferred.locals)

    def test_namedtuple_rename_duplicates(self) -> None:
        node = builder.extract_node(
            """
        from collections import namedtuple
        Tuple = namedtuple("Tuple", "abc abc abc", rename=True)
        Tuple #@
        """
        )
        inferred = next(node.infer())
        self.assertIn("abc", inferred.locals)
        self.assertIn("_1", inferred.locals)
        self.assertIn("_2", inferred.locals)

    def test_namedtuple_rename_uninferable(self) -> None:
        node = builder.extract_node(
            """
        from collections import namedtuple
        Tuple = namedtuple("Tuple", "a b c", rename=UNINFERABLE)
        Tuple #@
        """
        )
        inferred = next(node.infer())
        self.assertIn("a", inferred.locals)
        self.assertIn("b", inferred.locals)
        self.assertIn("c", inferred.locals)

    def test_namedtuple_func_form(self) -> None:
        node = builder.extract_node(
            """
        from collections import namedtuple
        Tuple = namedtuple(typename="Tuple", field_names="a b c", rename=UNINFERABLE)
        Tuple #@
        """
        )
        inferred = next(node.infer())
        self.assertEqual(inferred.name, "Tuple")
        self.assertIn("a", inferred.locals)
        self.assertIn("b", inferred.locals)
        self.assertIn("c", inferred.locals)

    def test_namedtuple_func_form_args_and_kwargs(self) -> None:
        node = builder.extract_node(
            """
        from collections import namedtuple
        Tuple = namedtuple("Tuple", field_names="a b c", rename=UNINFERABLE)
        Tuple #@
        """
        )
        inferred = next(node.infer())
        self.assertEqual(inferred.name, "Tuple")
        self.assertIn("a", inferred.locals)
        self.assertIn("b", inferred.locals)
        self.assertIn("c", inferred.locals)

    def test_namedtuple_bases_are_actually_names_not_nodes(self) -> None:
        node = builder.extract_node(
            """
        from collections import namedtuple
        Tuple = namedtuple("Tuple", field_names="a b c", rename=UNINFERABLE)
        Tuple #@
        """
        )
        inferred = next(node.infer())
        self.assertIsInstance(inferred, astroid.ClassDef)
        self.assertIsInstance(inferred.bases[0], astroid.Name)
        self.assertEqual(inferred.bases[0].name, "tuple")

    def test_invalid_label_does_not_crash_inference(self) -> None:
        code = """
        import collections
        a = collections.namedtuple( 'a', ['b c'] )
        a
        """
        node = builder.extract_node(code)
        inferred = next(node.infer())
        assert isinstance(inferred, astroid.ClassDef)
        assert "b" not in inferred.locals
        assert "c" not in inferred.locals

    def test_no_rename_duplicates_does_not_crash_inference(self) -> None:
        node = builder.extract_node(
            """
        from collections import namedtuple
        Tuple = namedtuple("Tuple", "abc abc")
        Tuple #@
        """
        )
        inferred = next(node.infer())
        self.assertIs(util.Uninferable, inferred)  # would raise ValueError

    def test_no_rename_keywords_does_not_crash_inference(self) -> None:
        node = builder.extract_node(
            """
        from collections import namedtuple
        Tuple = namedtuple("Tuple", "abc def")
        Tuple #@
        """
        )
        inferred = next(node.infer())
        self.assertIs(util.Uninferable, inferred)  # would raise ValueError

    def test_no_rename_nonident_does_not_crash_inference(self) -> None:
        node = builder.extract_node(
            """
        from collections import namedtuple
        Tuple = namedtuple("Tuple", "123 456")
        Tuple #@
        """
        )
        inferred = next(node.infer())
        self.assertIs(util.Uninferable, inferred)  # would raise ValueError

    def test_no_rename_underscore_does_not_crash_inference(self) -> None:
        node = builder.extract_node(
            """
        from collections import namedtuple
        Tuple = namedtuple("Tuple", "_1")
        Tuple #@
        """
        )
        inferred = next(node.infer())
        self.assertIs(util.Uninferable, inferred)  # would raise ValueError

    def test_invalid_typename_does_not_crash_inference(self) -> None:
        node = builder.extract_node(
            """
        from collections import namedtuple
        Tuple = namedtuple("123", "abc")
        Tuple #@
        """
        )
        inferred = next(node.infer())
        self.assertIs(util.Uninferable, inferred)  # would raise ValueError

    def test_keyword_typename_does_not_crash_inference(self) -> None:
        node = builder.extract_node(
            """
        from collections import namedtuple
        Tuple = namedtuple("while", "abc")
        Tuple #@
        """
        )
        inferred = next(node.infer())
        self.assertIs(util.Uninferable, inferred)  # would raise ValueError

    def test_typeerror_does_not_crash_inference(self) -> None:
        node = builder.extract_node(
            """
        from collections import namedtuple
        Tuple = namedtuple("Tuple", [123, 456])
        Tuple #@
        """
        )
        inferred = next(node.infer())
        # namedtuple converts all arguments to strings so these should be too
        # and catch on the isidentifier() check
        self.assertIs(util.Uninferable, inferred)

    def test_pathological_str_does_not_crash_inference(self) -> None:
        node = builder.extract_node(
            """
        from collections import namedtuple
        class Invalid:
            def __str__(self):
                return 123  # will raise TypeError
        Tuple = namedtuple("Tuple", [Invalid()])
        Tuple #@
        """
        )
        inferred = next(node.infer())
        self.assertIs(util.Uninferable, inferred)

    def test_name_as_typename(self) -> None:
        """Reported in https://github.com/pylint-dev/pylint/issues/7429 as a crash."""
        good_node, good_node_two, bad_node = builder.extract_node(
            """
            import collections
            collections.namedtuple(typename="MyTuple", field_names=["birth_date", "city"])  #@
            collections.namedtuple("MyTuple", field_names=["birth_date", "city"])  #@
            collections.namedtuple(["birth_date", "city"], typename="MyTuple")  #@
        """
        )
        good_inferred = next(good_node.infer())
        assert isinstance(good_inferred, nodes.ClassDef)
        good_node_two_inferred = next(good_node_two.infer())
        assert isinstance(good_node_two_inferred, nodes.ClassDef)
        bad_node_inferred = next(bad_node.infer())
        assert bad_node_inferred == util.Uninferable
