# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import unittest

import astroid
from astroid import exceptions, nodes

try:
    import attr  # type: ignore[import]  # pylint: disable=unused-import

    HAS_ATTR = True
except ImportError:
    HAS_ATTR = False


@unittest.skipUnless(HAS_ATTR, "These tests require the attr library")
class AttrsTest(unittest.TestCase):
    def test_attr_transform(self) -> None:
        module = astroid.parse(
            """
        import attr
        from attr import attrs, attrib, field

        @attr.s
        class Foo:

            d = attr.ib(attr.Factory(dict))

        f = Foo()
        f.d['answer'] = 42

        @attr.s(slots=True)
        class Bar:
            d = attr.ib(attr.Factory(dict))

        g = Bar()
        g.d['answer'] = 42

        @attrs
        class Bah:
            d = attrib(attr.Factory(dict))

        h = Bah()
        h.d['answer'] = 42

        @attr.attrs
        class Bai:
            d = attr.attrib(attr.Factory(dict))

        i = Bai()
        i.d['answer'] = 42

        @attr.define
        class Spam:
            d = field(default=attr.Factory(dict))

        j = Spam(d=1)
        j.d['answer'] = 42

        @attr.mutable
        class Eggs:
            d = attr.field(default=attr.Factory(dict))

        k = Eggs(d=1)
        k.d['answer'] = 42

        @attr.frozen
        class Eggs:
            d = attr.field(default=attr.Factory(dict))

        l = Eggs(d=1)
        l.d['answer'] = 42

        @attr.attrs(auto_attribs=True)
        class Eggs:
            d: int = attr.Factory(lambda: 3)

        m = Eggs(d=1)
        """
        )

        for name in ("f", "g", "h", "i", "j", "k", "l", "m"):
            should_be_unknown = next(module.getattr(name)[0].infer()).getattr("d")[0]
            self.assertIsInstance(should_be_unknown, astroid.Unknown)

    def test_attrs_transform(self) -> None:
        """Test brain for decorators of the 'attrs' package.

        Package added support for 'attrs' alongside 'attr' in v21.3.0.
        See: https://github.com/python-attrs/attrs/releases/tag/21.3.0
        """
        module = astroid.parse(
            """
        import attrs
        from attrs import field, mutable, frozen, define
        from attrs import mutable as my_mutable

        @attrs.define
        class Foo:

            d = attrs.field(attrs.Factory(dict))

        f = Foo()
        f.d['answer'] = 42

        @attrs.define(slots=True)
        class Bar:
            d = field(attrs.Factory(dict))

        g = Bar()
        g.d['answer'] = 42

        @attrs.mutable
        class Bah:
            d = field(attrs.Factory(dict))

        h = Bah()
        h.d['answer'] = 42

        @attrs.frozen
        class Bai:
            d = attrs.field(attrs.Factory(dict))

        i = Bai()
        i.d['answer'] = 42

        @attrs.define
        class Spam:
            d = field(default=attrs.Factory(dict))

        j = Spam(d=1)
        j.d['answer'] = 42

        @attrs.mutable
        class Eggs:
            d = attrs.field(default=attrs.Factory(dict))

        k = Eggs(d=1)
        k.d['answer'] = 42

        @attrs.frozen
        class Eggs:
            d = attrs.field(default=attrs.Factory(dict))

        l = Eggs(d=1)
        l.d['answer'] = 42


        @frozen
        class Legs:
            d = attrs.field(default=attrs.Factory(dict))
        """
        )

        for name in ("f", "g", "h", "i", "j", "k", "l"):
            should_be_unknown = next(module.getattr(name)[0].infer()).getattr("d")[0]
            self.assertIsInstance(should_be_unknown, astroid.Unknown, name)

    def test_special_attributes(self) -> None:
        """Make sure special attrs attributes exist"""

        code = """
        import attr

        @attr.s
        class Foo:
            pass
        Foo()
        """
        foo_inst = next(astroid.extract_node(code).infer())
        [attr_node] = foo_inst.getattr("__attrs_attrs__")
        # Prevents https://github.com/pylint-dev/pylint/issues/1884
        assert isinstance(attr_node, nodes.Unknown)

    def test_dont_consider_assignments_but_without_attrs(self) -> None:
        code = """
        import attr

        class Cls: pass
        @attr.s
        class Foo:
            temp = Cls()
            temp.prop = 5
            bar_thing = attr.ib(default=temp)
        Foo()
        """
        next(astroid.extract_node(code).infer())

    def test_attrs_with_annotation(self) -> None:
        code = """
        import attr

        @attr.s
        class Foo:
            bar: int = attr.ib(default=5)
        Foo()
        """
        should_be_unknown = next(astroid.extract_node(code).infer()).getattr("bar")[0]
        self.assertIsInstance(should_be_unknown, astroid.Unknown)

    def test_attr_with_only_annotation_fails(self) -> None:
        code = """
        import attr

        @attr.s
        class Foo:
            bar: int
        Foo()
        """
        with self.assertRaises(exceptions.AttributeInferenceError):
            next(astroid.extract_node(code).infer()).getattr("bar")

    def test_attrs_with_only_annotation_works(self) -> None:
        code = """
        import attrs

        @attrs.define
        class Foo:
            bar: int
            baz: str = "hello"
        Foo(1)
        """
        for attr_name in ("bar", "baz"):
            should_be_unknown = next(astroid.extract_node(code).infer()).getattr(
                attr_name
            )[0]
            self.assertIsInstance(should_be_unknown, astroid.Unknown)
