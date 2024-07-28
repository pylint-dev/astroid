# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import io
import re
import sys
import unittest

import pytest

import astroid
from astroid import MANAGER, builder, nodes, objects, test_utils, util
from astroid.bases import Instance
from astroid.brain.brain_namedtuple_enum import _get_namedtuple_fields
from astroid.const import PY312_PLUS, PY313_PLUS
from astroid.exceptions import (
    AttributeInferenceError,
    InferenceError,
    UseInferenceDefault,
)
from astroid.nodes.node_classes import Const
from astroid.nodes.scoped_nodes import ClassDef


def assertEqualMro(klass: ClassDef, expected_mro: list[str]) -> None:
    """Check mro names."""
    assert [member.qname() for member in klass.mro()] == expected_mro


class CollectionsDequeTests(unittest.TestCase):
    def _inferred_queue_instance(self) -> Instance:
        node = builder.extract_node(
            """
        import collections
        q = collections.deque([])
        q
        """
        )
        return next(node.infer())

    def test_deque(self) -> None:
        inferred = self._inferred_queue_instance()
        self.assertTrue(inferred.getattr("__len__"))

    def test_deque_py35methods(self) -> None:
        inferred = self._inferred_queue_instance()
        self.assertIn("copy", inferred.locals)
        self.assertIn("insert", inferred.locals)
        self.assertIn("index", inferred.locals)

    def test_deque_py39methods(self):
        inferred = self._inferred_queue_instance()
        self.assertTrue(inferred.getattr("__class_getitem__"))


class OrderedDictTest(unittest.TestCase):
    def _inferred_ordered_dict_instance(self) -> Instance:
        node = builder.extract_node(
            """
        import collections
        d = collections.OrderedDict()
        d
        """
        )
        return next(node.infer())

    def test_ordered_dict_py34method(self) -> None:
        inferred = self._inferred_ordered_dict_instance()
        self.assertIn("move_to_end", inferred.locals)


class DefaultDictTest(unittest.TestCase):
    def test_1(self) -> None:
        node = builder.extract_node(
            """
        from collections import defaultdict

        X = defaultdict(int)
        X[0]
        """
        )
        inferred = next(node.infer())
        self.assertIs(util.Uninferable, inferred)


class ModuleExtenderTest(unittest.TestCase):
    def test_extension_modules(self) -> None:
        transformer = MANAGER._transform
        for extender, _ in transformer.transforms[nodes.Module]:
            n = nodes.Module("__main__")
            extender(n)


def streams_are_fine():
    """Check if streams are being overwritten,
    for example, by pytest

    stream inference will not work if they are overwritten

    PY3 only
    """
    return all(isinstance(s, io.IOBase) for s in (sys.stdout, sys.stderr, sys.stdin))


class IOBrainTest(unittest.TestCase):
    @unittest.skipUnless(
        streams_are_fine(),
        "Needs Python 3 io model / doesn't work with plain pytest."
        "use pytest -s for this test to work",
    )
    def test_sys_streams(self):
        for name in ("stdout", "stderr", "stdin"):
            node = astroid.extract_node(
                f"""
            import sys
            sys.{name}
            """
            )
            inferred = next(node.infer())
            buffer_attr = next(inferred.igetattr("buffer"))
            self.assertIsInstance(buffer_attr, astroid.Instance)
            self.assertEqual(buffer_attr.name, "BufferedWriter")
            raw = next(buffer_attr.igetattr("raw"))
            self.assertIsInstance(raw, astroid.Instance)
            self.assertEqual(raw.name, "FileIO")


@test_utils.require_version("3.9")
class TypeBrain(unittest.TestCase):
    def test_type_subscript(self):
        """
        Check that type object has the __class_getitem__ method
        when it is used as a subscript
        """
        src = builder.extract_node(
            """
            a: type[int] = int
            """
        )
        val_inf = src.annotation.value.inferred()[0]
        self.assertIsInstance(val_inf, astroid.ClassDef)
        self.assertEqual(val_inf.name, "type")
        meth_inf = val_inf.getattr("__class_getitem__")[0]
        self.assertIsInstance(meth_inf, astroid.FunctionDef)

    def test_invalid_type_subscript(self):
        """
        Check that a type (str for example) that inherits
        from type does not have __class_getitem__ method even
        when it is used as a subscript
        """
        src = builder.extract_node(
            """
            a: str[int] = "abc"
            """
        )
        val_inf = src.annotation.value.inferred()[0]
        self.assertIsInstance(val_inf, astroid.ClassDef)
        self.assertEqual(val_inf.name, "str")
        with self.assertRaises(AttributeInferenceError):
            # pylint: disable=expression-not-assigned
            # noinspection PyStatementEffect
            val_inf.getattr("__class_getitem__")[0]

    def test_builtin_subscriptable(self):
        """Starting with python3.9 builtin types such as list are subscriptable.
        Any builtin class such as "enumerate" or "staticmethod" also works."""
        for typename in ("tuple", "list", "dict", "set", "frozenset", "enumerate"):
            src = f"""
            {typename:s}[int]
            """
            right_node = builder.extract_node(src)
            inferred = next(right_node.infer())
            self.assertIsInstance(inferred, nodes.ClassDef)
            self.assertIsInstance(inferred.getattr("__iter__")[0], nodes.FunctionDef)


def check_metaclass_is_abc(node: nodes.ClassDef):
    if PY312_PLUS and node.name == "ByteString":
        # .metaclass() finds the first metaclass in the mro(),
        # which, from 3.12, is _DeprecateByteStringMeta (unhelpful)
        # until ByteString is removed in 3.14.
        # Jump over the first two ByteString classes in the mro().
        check_metaclass_is_abc(node.mro()[2])
    else:
        meta = node.metaclass()
        assert isinstance(meta, nodes.ClassDef)
        assert meta.name == "ABCMeta"


class CollectionsBrain(unittest.TestCase):
    def test_collections_object_not_subscriptable(self) -> None:
        """
        Test that unsubscriptable types are detected
        Hashable is not subscriptable even with python39
        """
        wrong_node = builder.extract_node(
            """
        import collections.abc
        collections.abc.Hashable[int]
        """
        )
        with self.assertRaises(InferenceError):
            next(wrong_node.infer())
        right_node = builder.extract_node(
            """
        import collections.abc
        collections.abc.Hashable
        """
        )
        inferred = next(right_node.infer())
        check_metaclass_is_abc(inferred)
        assertEqualMro(
            inferred,
            [
                "_collections_abc.Hashable",
                "builtins.object",
            ],
        )
        with self.assertRaises(AttributeInferenceError):
            inferred.getattr("__class_getitem__")

    def test_collections_object_subscriptable(self):
        """Starting with python39 some object of collections module are subscriptable. Test one of them"""
        right_node = builder.extract_node(
            """
        import collections.abc
        collections.abc.MutableSet[int]
        """
        )
        inferred = next(right_node.infer())
        check_metaclass_is_abc(inferred)
        assertEqualMro(
            inferred,
            [
                "_collections_abc.MutableSet",
                "_collections_abc.Set",
                "_collections_abc.Collection",
                "_collections_abc.Sized",
                "_collections_abc.Iterable",
                "_collections_abc.Container",
                "builtins.object",
            ],
        )
        self.assertIsInstance(
            inferred.getattr("__class_getitem__")[0], nodes.FunctionDef
        )

    @test_utils.require_version(maxver="3.9")
    def test_collections_object_not_yet_subscriptable(self):
        """
        Test that unsubscriptable types are detected as such.
        Until python39 MutableSet of the collections module is not subscriptable.
        """
        wrong_node = builder.extract_node(
            """
        import collections.abc
        collections.abc.MutableSet[int]
        """
        )
        with self.assertRaises(InferenceError):
            next(wrong_node.infer())
        right_node = builder.extract_node(
            """
        import collections.abc
        collections.abc.MutableSet
        """
        )
        inferred = next(right_node.infer())
        check_metaclass_is_abc(inferred)
        assertEqualMro(
            inferred,
            [
                "_collections_abc.MutableSet",
                "_collections_abc.Set",
                "_collections_abc.Collection",
                "_collections_abc.Sized",
                "_collections_abc.Iterable",
                "_collections_abc.Container",
                "builtins.object",
            ],
        )
        with self.assertRaises(AttributeInferenceError):
            inferred.getattr("__class_getitem__")

    def test_collections_object_subscriptable_2(self):
        """Starting with python39 Iterator in the collection.abc module is subscriptable"""
        node = builder.extract_node(
            """
        import collections.abc
        class Derived(collections.abc.Iterator[int]):
            pass
        """
        )
        inferred = next(node.infer())
        check_metaclass_is_abc(inferred)
        assertEqualMro(
            inferred,
            [
                ".Derived",
                "_collections_abc.Iterator",
                "_collections_abc.Iterable",
                "builtins.object",
            ],
        )

    @test_utils.require_version(maxver="3.9")
    def test_collections_object_not_yet_subscriptable_2(self):
        """Before python39 Iterator in the collection.abc module is not subscriptable"""
        node = builder.extract_node(
            """
        import collections.abc
        collections.abc.Iterator[int]
        """
        )
        with self.assertRaises(InferenceError):
            next(node.infer())

    def test_collections_object_subscriptable_3(self):
        """With Python 3.9 the ByteString class of the collections module is subscriptable
        (but not the same class from typing module)"""
        right_node = builder.extract_node(
            """
        import collections.abc
        collections.abc.ByteString[int]
        """
        )
        inferred = next(right_node.infer())
        check_metaclass_is_abc(inferred)
        self.assertIsInstance(
            inferred.getattr("__class_getitem__")[0], nodes.FunctionDef
        )

    def test_collections_object_subscriptable_4(self):
        """Multiple inheritance with subscriptable collection class"""
        node = builder.extract_node(
            """
        import collections.abc
        class Derived(collections.abc.Hashable, collections.abc.Iterator[int]):
            pass
        """
        )
        inferred = next(node.infer())
        assertEqualMro(
            inferred,
            [
                ".Derived",
                "_collections_abc.Hashable",
                "_collections_abc.Iterator",
                "_collections_abc.Iterable",
                "builtins.object",
            ],
        )


class TypingBrain(unittest.TestCase):
    def test_namedtuple_base(self) -> None:
        klass = builder.extract_node(
            """
        from typing import NamedTuple

        class X(NamedTuple("X", [("a", int), ("b", str), ("c", bytes)])):
           pass
        """
        )
        self.assertEqual(
            [anc.name for anc in klass.ancestors()], ["X", "tuple", "object"]
        )
        for anc in klass.ancestors():
            self.assertFalse(anc.parent is None)

    def test_namedtuple_can_correctly_access_methods(self) -> None:
        klass, called = builder.extract_node(
            """
        from typing import NamedTuple

        class X(NamedTuple): #@
            a: int
            b: int
            def as_string(self):
                return '%s' % self.a
            def as_integer(self):
                return 2 + 3
        X().as_integer() #@
        """
        )
        self.assertEqual(len(klass.getattr("as_string")), 1)
        inferred = next(called.infer())
        self.assertIsInstance(inferred, astroid.Const)
        self.assertEqual(inferred.value, 5)

    def test_namedtuple_inference(self) -> None:
        klass = builder.extract_node(
            """
        from typing import NamedTuple

        class X(NamedTuple("X", [("a", int), ("b", str), ("c", bytes)])):
           pass
        """
        )
        base = next(base for base in klass.ancestors() if base.name == "X")
        self.assertSetEqual({"a", "b", "c"}, set(base.instance_attrs))

    def test_namedtuple_inference_nonliteral(self) -> None:
        # Note: NamedTuples in mypy only work with literals.
        klass = builder.extract_node(
            """
        from typing import NamedTuple

        name = "X"
        fields = [("a", int), ("b", str), ("c", bytes)]
        NamedTuple(name, fields)
        """
        )
        inferred = next(klass.infer())
        self.assertIsInstance(inferred, astroid.Instance)
        self.assertEqual(inferred.qname(), "typing.NamedTuple")

    def test_namedtuple_instance_attrs(self) -> None:
        result = builder.extract_node(
            """
        from typing import NamedTuple
        NamedTuple("A", [("a", int), ("b", str), ("c", bytes)])(1, 2, 3) #@
        """
        )
        inferred = next(result.infer())
        for name, attr in inferred.instance_attrs.items():
            self.assertEqual(attr[0].attrname, name)

    def test_namedtuple_simple(self) -> None:
        result = builder.extract_node(
            """
        from typing import NamedTuple
        NamedTuple("A", [("a", int), ("b", str), ("c", bytes)])
        """
        )
        inferred = next(result.infer())
        self.assertIsInstance(inferred, nodes.ClassDef)
        self.assertSetEqual({"a", "b", "c"}, set(inferred.instance_attrs))

    def test_namedtuple_few_args(self) -> None:
        result = builder.extract_node(
            """
        from typing import NamedTuple
        NamedTuple("A")
        """
        )
        inferred = next(result.infer())
        self.assertIsInstance(inferred, astroid.Instance)
        self.assertEqual(inferred.qname(), "typing.NamedTuple")

    def test_namedtuple_few_fields(self) -> None:
        result = builder.extract_node(
            """
        from typing import NamedTuple
        NamedTuple("A", [("a",), ("b", str), ("c", bytes)])
        """
        )
        inferred = next(result.infer())
        self.assertIsInstance(inferred, astroid.Instance)
        self.assertEqual(inferred.qname(), "typing.NamedTuple")

    def test_namedtuple_class_form(self) -> None:
        result = builder.extract_node(
            """
        from typing import NamedTuple

        class Example(NamedTuple):
            CLASS_ATTR = "class_attr"
            mything: int

        Example(mything=1)
        """
        )
        inferred = next(result.infer())
        self.assertIsInstance(inferred, astroid.Instance)

        class_attr = inferred.getattr("CLASS_ATTR")[0]
        self.assertIsInstance(class_attr, astroid.AssignName)
        const = next(class_attr.infer())
        self.assertEqual(const.value, "class_attr")

    def test_namedtuple_inferred_as_class(self) -> None:
        node = builder.extract_node(
            """
        from typing import NamedTuple
        NamedTuple
        """
        )
        inferred = next(node.infer())
        assert isinstance(inferred, nodes.ClassDef)
        assert inferred.name == "NamedTuple"

    def test_namedtuple_bug_pylint_4383(self) -> None:
        """Inference of 'NamedTuple' function shouldn't cause InferenceError.

        https://github.com/pylint-dev/pylint/issues/4383
        """
        node = builder.extract_node(
            """
        if True:
            def NamedTuple():
                pass
        NamedTuple
        """
        )
        next(node.infer())

    def test_namedtuple_uninferable_member(self) -> None:
        call = builder.extract_node(
            """
        from typing import namedtuple
        namedtuple('uninf', {x: x for x in range(0)})  #@"""
        )
        with pytest.raises(UseInferenceDefault):
            _get_namedtuple_fields(call)

        call = builder.extract_node(
            """
        from typing import namedtuple
        uninferable = {x: x for x in range(0)}
        namedtuple('uninferable', uninferable)  #@
        """
        )
        with pytest.raises(UseInferenceDefault):
            _get_namedtuple_fields(call)

    def test_typing_types(self) -> None:
        ast_nodes = builder.extract_node(
            """
        from typing import TypeVar, Iterable, Tuple, NewType, Dict, Union
        TypeVar('MyTypeVar', int, float, complex) #@
        Iterable[Tuple[MyTypeVar, MyTypeVar]] #@
        TypeVar('AnyStr', str, bytes) #@
        NewType('UserId', str) #@
        Dict[str, str] #@
        Union[int, str] #@
        """
        )
        for node in ast_nodes:
            inferred = next(node.infer())
            self.assertIsInstance(inferred, nodes.ClassDef, node.as_string())

    def test_typing_type_without_tip(self):
        """Regression test for https://github.com/pylint-dev/pylint/issues/5770"""
        node = builder.extract_node(
            """
        from typing import NewType

        def make_new_type(t):
            new_type = NewType(f'IntRange_{t}', t) #@
        """
        )
        with self.assertRaises(UseInferenceDefault):
            astroid.brain.brain_typing.infer_typing_typevar_or_newtype(node.value)

    def test_namedtuple_nested_class(self):
        result = builder.extract_node(
            """
        from typing import NamedTuple

        class Example(NamedTuple):
            class Foo:
                bar = "bar"

        Example
        """
        )
        inferred = next(result.infer())
        self.assertIsInstance(inferred, astroid.ClassDef)

        class_def_attr = inferred.getattr("Foo")[0]
        self.assertIsInstance(class_def_attr, astroid.ClassDef)
        attr_def = class_def_attr.getattr("bar")[0]
        attr = next(attr_def.infer())
        self.assertEqual(attr.value, "bar")

    def test_tuple_type(self):
        node = builder.extract_node(
            """
        from typing import Tuple
        Tuple[int, int]
        """
        )
        inferred = next(node.infer())
        assert isinstance(inferred, nodes.ClassDef)
        assert isinstance(inferred.getattr("__class_getitem__")[0], nodes.FunctionDef)
        assert inferred.qname() == "typing.Tuple"

    def test_callable_type(self):
        node = builder.extract_node(
            """
        from typing import Callable, Any
        Callable[..., Any]
        """
        )
        inferred = next(node.infer())
        assert isinstance(inferred, nodes.ClassDef)
        assert isinstance(inferred.getattr("__class_getitem__")[0], nodes.FunctionDef)
        assert inferred.qname() == "typing.Callable"

    def test_typing_generic_subscriptable(self):
        """Test typing.Generic is subscriptable with __class_getitem__ (added in PY37)"""
        node = builder.extract_node(
            """
        from typing import Generic, TypeVar
        T = TypeVar('T')
        Generic[T]
        """
        )
        inferred = next(node.infer())
        assert isinstance(inferred, nodes.ClassDef)
        assert isinstance(inferred.getattr("__class_getitem__")[0], nodes.FunctionDef)

    @test_utils.require_version(minver="3.12")
    def test_typing_generic_subscriptable_pep695(self):
        """Test class using type parameters is subscriptable with __class_getitem__ (added in PY312)"""
        node = builder.extract_node(
            """
        class Foo[T]: ...
        class Bar[T](Foo[T]): ...
        """
        )
        inferred = next(node.infer())
        assert isinstance(inferred, nodes.ClassDef)
        assert inferred.name == "Bar"
        assert isinstance(inferred.getattr("__class_getitem__")[0], nodes.FunctionDef)
        ancestors = list(inferred.ancestors())
        assert len(ancestors) == 2
        assert ancestors[0].name == "Foo"
        assert ancestors[1].name == "object"

    def test_typing_annotated_subscriptable(self):
        """typing.Annotated is subscriptable with __class_getitem__ below 3.13."""
        node = builder.extract_node(
            """
        import typing
        typing.Annotated[str, "data"]
        """
        )
        inferred = next(node.infer())
        if PY313_PLUS:
            assert isinstance(inferred, nodes.FunctionDef)
        else:
            assert isinstance(inferred, nodes.ClassDef)
            assert isinstance(
                inferred.getattr("__class_getitem__")[0], nodes.FunctionDef
            )

    def test_typing_generic_slots(self):
        """Test slots for Generic subclass."""
        node = builder.extract_node(
            """
        from typing import Generic, TypeVar
        T = TypeVar('T')
        class A(Generic[T]):
            __slots__ = ['value']
            def __init__(self, value):
                self.value = value
        """
        )
        inferred = next(node.infer())
        slots = inferred.slots()
        assert len(slots) == 1
        assert isinstance(slots[0], nodes.Const)
        assert slots[0].value == "value"

    def test_typing_no_duplicates(self):
        node = builder.extract_node(
            """
        from typing import List
        List[int]
        """
        )
        assert len(node.inferred()) == 1

    def test_typing_no_duplicates_2(self):
        node = builder.extract_node(
            """
        from typing import Optional, Tuple
        Tuple[Optional[int], ...]
        """
        )
        assert len(node.inferred()) == 1

    @test_utils.require_version(minver="3.10")
    def test_typing_param_spec(self):
        node = builder.extract_node(
            """
        from typing import ParamSpec

        P = ParamSpec("P")
        """
        )
        inferred = next(node.targets[0].infer())
        assert next(inferred.igetattr("args")) is not None
        assert next(inferred.igetattr("kwargs")) is not None

    def test_collections_generic_alias_slots(self):
        """Test slots for a class which is a subclass of a generic alias type."""
        node = builder.extract_node(
            """
        import collections
        import typing
        Type = typing.TypeVar('Type')
        class A(collections.abc.AsyncIterator[Type]):
            __slots__ = ('_value',)
            def __init__(self, value: collections.abc.AsyncIterator[Type]):
                self._value = value
        """
        )
        inferred = next(node.infer())
        assert isinstance(inferred, nodes.ClassDef)
        slots = inferred.slots()
        assert len(slots) == 1
        assert isinstance(slots[0], nodes.Const)
        assert slots[0].value == "_value"

    def test_has_dunder_args(self) -> None:
        ast_node = builder.extract_node(
            """
        from typing import Union
        NumericTypes = Union[int, float]
        NumericTypes.__args__ #@
        """
        )
        inferred = next(ast_node.infer())
        assert isinstance(inferred, nodes.Tuple)

    def test_typing_namedtuple_dont_crash_on_no_fields(self) -> None:
        node = builder.extract_node(
            """
        from typing import NamedTuple

        Bar = NamedTuple("bar", [])

        Bar()
        """
        )
        inferred = next(node.infer())
        self.assertIsInstance(inferred, astroid.Instance)

    def test_typed_dict(self):
        code = builder.extract_node(
            """
        from typing import TypedDict
        class CustomTD(TypedDict):  #@
            var: int
        CustomTD(var=1)  #@
        """
        )
        inferred_base = next(code[0].bases[0].infer())
        assert isinstance(inferred_base, nodes.ClassDef)
        assert inferred_base.qname() == "typing.TypedDict"
        typedDict_base = next(inferred_base.bases[0].infer())
        assert typedDict_base.qname() == "builtins.dict"

        # Test TypedDict has `__call__` method
        local_call = inferred_base.locals.get("__call__", None)
        assert local_call and len(local_call) == 1
        assert isinstance(local_call[0], nodes.Name) and local_call[0].name == "dict"

        # Test TypedDict instance is callable
        assert next(code[1].infer()).callable() is True

    def test_typing_alias_type(self):
        """
        Test that the type aliased thanks to typing._alias function are
        correctly inferred.
        typing_alias function is introduced with python37
        """
        node = builder.extract_node(
            """
        from typing import TypeVar, MutableSet

        T = TypeVar("T")
        MutableSet[T]

        class Derived1(MutableSet[T]):
            pass
        """
        )
        inferred = next(node.infer())
        assertEqualMro(
            inferred,
            [
                ".Derived1",
                "typing.MutableSet",
                "_collections_abc.MutableSet",
                "_collections_abc.Set",
                "_collections_abc.Collection",
                "_collections_abc.Sized",
                "_collections_abc.Iterable",
                "_collections_abc.Container",
                "builtins.object",
            ],
        )

    def test_typing_alias_type_2(self):
        """
        Test that the type aliased thanks to typing._alias function are
        correctly inferred.
        typing_alias function is introduced with python37.
        OrderedDict in the typing module appears only with python 3.7.2
        """
        node = builder.extract_node(
            """
        import typing
        class Derived2(typing.OrderedDict[int, str]):
            pass
        """
        )
        inferred = next(node.infer())
        assertEqualMro(
            inferred,
            [
                ".Derived2",
                "typing.OrderedDict",
                "collections.OrderedDict",
                "builtins.dict",
                "builtins.object",
            ],
        )

    def test_typing_object_not_subscriptable(self):
        """Hashable is not subscriptable"""
        wrong_node = builder.extract_node(
            """
        import typing
        typing.Hashable[int]
        """
        )
        with self.assertRaises(InferenceError):
            next(wrong_node.infer())
        right_node = builder.extract_node(
            """
        import typing
        typing.Hashable
        """
        )
        inferred = next(right_node.infer())
        assertEqualMro(
            inferred,
            [
                "typing.Hashable",
                "_collections_abc.Hashable",
                "builtins.object",
            ],
        )
        with self.assertRaises(AttributeInferenceError):
            inferred.getattr("__class_getitem__")

    def test_typing_object_subscriptable(self):
        """Test that MutableSet is subscriptable"""
        right_node = builder.extract_node(
            """
        import typing
        typing.MutableSet[int]
        """
        )
        inferred = next(right_node.infer())
        assertEqualMro(
            inferred,
            [
                "typing.MutableSet",
                "_collections_abc.MutableSet",
                "_collections_abc.Set",
                "_collections_abc.Collection",
                "_collections_abc.Sized",
                "_collections_abc.Iterable",
                "_collections_abc.Container",
                "builtins.object",
            ],
        )
        self.assertIsInstance(
            inferred.getattr("__class_getitem__")[0], nodes.FunctionDef
        )

    def test_typing_object_subscriptable_2(self):
        """Multiple inheritance with subscriptable typing alias"""
        node = builder.extract_node(
            """
        import typing
        class Derived(typing.Hashable, typing.Iterator[int]):
            pass
        """
        )
        inferred = next(node.infer())
        assertEqualMro(
            inferred,
            [
                ".Derived",
                "typing.Hashable",
                "_collections_abc.Hashable",
                "typing.Iterator",
                "_collections_abc.Iterator",
                "_collections_abc.Iterable",
                "builtins.object",
            ],
        )

    def test_typing_object_notsubscriptable_3(self):
        """Until python39 ByteString class of the typing module is not
        subscriptable (whereas it is in the collections' module)"""
        right_node = builder.extract_node(
            """
        import typing
        typing.ByteString
        """
        )
        inferred = next(right_node.infer())
        check_metaclass_is_abc(inferred)
        with self.assertRaises(AttributeInferenceError):
            self.assertIsInstance(
                inferred.getattr("__class_getitem__")[0], nodes.FunctionDef
            )

    def test_typing_object_builtin_subscriptable(self):
        """
        Test that builtins alias, such as typing.List, are subscriptable
        """
        for typename in ("List", "Dict", "Set", "FrozenSet", "Tuple"):
            src = f"""
            import typing
            typing.{typename:s}[int]
            """
            right_node = builder.extract_node(src)
            inferred = next(right_node.infer())
            self.assertIsInstance(inferred, nodes.ClassDef)
            self.assertIsInstance(inferred.getattr("__iter__")[0], nodes.FunctionDef)

    @staticmethod
    def test_typing_type_subscriptable():
        node = builder.extract_node(
            """
        from typing import Type
        Type[int]
        """
        )
        inferred = next(node.infer())
        assert isinstance(inferred, nodes.ClassDef)
        assert isinstance(inferred.getattr("__class_getitem__")[0], nodes.FunctionDef)
        assert inferred.qname() == "typing.Type"

    def test_typing_cast(self) -> None:
        node = builder.extract_node(
            """
        from typing import cast
        class A:
            pass

        b = 42
        cast(A, b)
        """
        )
        inferred = next(node.infer())
        assert isinstance(inferred, nodes.Const)
        assert inferred.value == 42

    def test_typing_cast_attribute(self) -> None:
        node = builder.extract_node(
            """
        import typing
        class A:
            pass

        b = 42
        typing.cast(A, b)
        """
        )
        inferred = next(node.infer())
        assert isinstance(inferred, nodes.Const)
        assert inferred.value == 42

    def test_typing_cast_multiple_inference_calls(self) -> None:
        """Inference of an outer function should not store the result for cast."""
        ast_nodes = builder.extract_node(
            """
        from typing import TypeVar, cast
        T = TypeVar("T")
        def ident(var: T) -> T:
            return cast(T, var)

        ident(2)  #@
        ident("Hello")  #@
        """
        )
        i0 = next(ast_nodes[0].infer())
        assert isinstance(i0, nodes.Const)
        assert i0.value == 2

        i1 = next(ast_nodes[1].infer())
        assert isinstance(i1, nodes.Const)
        assert i1.value == "Hello"


class ReBrainTest(unittest.TestCase):
    def test_regex_flags(self) -> None:
        names = [name for name in dir(re) if name.isupper()]
        re_ast = MANAGER.ast_from_module_name("re")
        for name in names:
            self.assertIn(name, re_ast)
            self.assertEqual(next(re_ast[name].infer()).value, getattr(re, name))

    @test_utils.require_version(maxver="3.9")
    def test_re_pattern_unsubscriptable(self):
        """
        re.Pattern and re.Match are unsubscriptable until PY39.
        """
        right_node1 = builder.extract_node(
            """
        import re
        re.Pattern
        """
        )
        inferred1 = next(right_node1.infer())
        assert isinstance(inferred1, nodes.ClassDef)
        with self.assertRaises(AttributeInferenceError):
            assert isinstance(
                inferred1.getattr("__class_getitem__")[0], nodes.FunctionDef
            )

        right_node2 = builder.extract_node(
            """
        import re
        re.Pattern
        """
        )
        inferred2 = next(right_node2.infer())
        assert isinstance(inferred2, nodes.ClassDef)
        with self.assertRaises(AttributeInferenceError):
            assert isinstance(
                inferred2.getattr("__class_getitem__")[0], nodes.FunctionDef
            )

        wrong_node1 = builder.extract_node(
            """
        import re
        re.Pattern[int]
        """
        )
        with self.assertRaises(InferenceError):
            next(wrong_node1.infer())

        wrong_node2 = builder.extract_node(
            """
        import re
        re.Match[int]
        """
        )
        with self.assertRaises(InferenceError):
            next(wrong_node2.infer())

    def test_re_pattern_subscriptable(self):
        """Test re.Pattern and re.Match are subscriptable in PY39+"""
        node1 = builder.extract_node(
            """
        import re
        re.Pattern[str]
        """
        )
        inferred1 = next(node1.infer())
        assert isinstance(inferred1, nodes.ClassDef)
        assert isinstance(inferred1.getattr("__class_getitem__")[0], nodes.FunctionDef)

        node2 = builder.extract_node(
            """
        import re
        re.Match[str]
        """
        )
        inferred2 = next(node2.infer())
        assert isinstance(inferred2, nodes.ClassDef)
        assert isinstance(inferred2.getattr("__class_getitem__")[0], nodes.FunctionDef)


class BrainNamedtupleAnnAssignTest(unittest.TestCase):
    def test_no_crash_on_ann_assign_in_namedtuple(self) -> None:
        node = builder.extract_node(
            """
        from enum import Enum
        from typing import Optional

        class A(Enum):
            B: str = 'B'
        """
        )
        inferred = next(node.infer())
        self.assertIsInstance(inferred, nodes.ClassDef)


class BrainUUIDTest(unittest.TestCase):
    def test_uuid_has_int_member(self) -> None:
        node = builder.extract_node(
            """
        import uuid
        u = uuid.UUID('{12345678-1234-5678-1234-567812345678}')
        u.int
        """
        )
        inferred = next(node.infer())
        self.assertIsInstance(inferred, nodes.Const)


class RandomSampleTest(unittest.TestCase):
    def test_inferred_successfully(self) -> None:
        node = astroid.extract_node(
            """
        import random
        random.sample([1, 2], 2) #@
        """
        )
        inferred = next(node.infer())
        self.assertIsInstance(inferred, astroid.List)
        elems = sorted(elem.value for elem in inferred.elts)
        self.assertEqual(elems, [1, 2])

    def test_arguments_inferred_successfully(self) -> None:
        """Test inference of `random.sample` when both arguments are of type `nodes.Call`."""
        node = astroid.extract_node(
            """
        import random

        def sequence():
            return [1, 2]

        random.sample(sequence(), len([1,2])) #@
        """
        )
        # Check that arguments are of type `nodes.Call`.
        sequence, length = node.args
        self.assertIsInstance(sequence, astroid.Call)
        self.assertIsInstance(length, astroid.Call)

        # Check the inference of `random.sample` call.
        inferred = next(node.infer())
        self.assertIsInstance(inferred, astroid.List)
        elems = sorted(elem.value for elem in inferred.elts)
        self.assertEqual(elems, [1, 2])

    def test_no_crash_on_evaluatedobject(self) -> None:
        node = astroid.extract_node(
            """
        from random import sample
        class A: pass
        sample(list({1: A()}.values()), 1)"""
        )
        inferred = next(node.infer())
        assert isinstance(inferred, astroid.List)
        assert len(inferred.elts) == 1
        assert isinstance(inferred.elts[0], nodes.Call)


class SubprocessTest(unittest.TestCase):
    """Test subprocess brain"""

    def test_subprocess_args(self) -> None:
        """Make sure the args attribute exists for Popen

        Test for https://github.com/pylint-dev/pylint/issues/1860"""
        name = astroid.extract_node(
            """
        import subprocess
        p = subprocess.Popen(['ls'])
        p #@
        """
        )
        [inst] = name.inferred()
        self.assertIsInstance(next(inst.igetattr("args")), nodes.List)

    def test_subprcess_check_output(self) -> None:
        code = """
        import subprocess

        subprocess.check_output(['echo', 'hello']);
        """
        node = astroid.extract_node(code)
        inferred = next(node.infer())
        # Can be either str or bytes
        assert isinstance(inferred, astroid.Const)
        assert isinstance(inferred.value, (str, bytes))

    @test_utils.require_version("3.9")
    def test_popen_does_not_have_class_getitem(self):
        code = """import subprocess; subprocess.Popen"""
        node = astroid.extract_node(code)
        inferred = next(node.infer())
        assert "__class_getitem__" in inferred


class TestIsinstanceInference:
    """Test isinstance builtin inference"""

    def test_type_type(self) -> None:
        assert _get_result("isinstance(type, type)") == "True"

    def test_object_type(self) -> None:
        assert _get_result("isinstance(object, type)") == "True"

    def test_type_object(self) -> None:
        assert _get_result("isinstance(type, object)") == "True"

    def test_isinstance_int_true(self) -> None:
        """Make sure isinstance can check builtin int types"""
        assert _get_result("isinstance(1, int)") == "True"

    def test_isinstance_int_false(self) -> None:
        assert _get_result("isinstance('a', int)") == "False"

    def test_isinstance_object_true(self) -> None:
        assert (
            _get_result(
                """
        class Bar(object):
            pass
        isinstance(Bar(), object)
        """
            )
            == "True"
        )

    def test_isinstance_object_true3(self) -> None:
        assert (
            _get_result(
                """
        class Bar(object):
            pass
        isinstance(Bar(), Bar)
        """
            )
            == "True"
        )

    def test_isinstance_class_false(self) -> None:
        assert (
            _get_result(
                """
        class Foo(object):
            pass
        class Bar(object):
            pass
        isinstance(Bar(), Foo)
        """
            )
            == "False"
        )

    def test_isinstance_type_false(self) -> None:
        assert (
            _get_result(
                """
        class Bar(object):
            pass
        isinstance(Bar(), type)
        """
            )
            == "False"
        )

    def test_isinstance_str_true(self) -> None:
        """Make sure isinstance can check builtin str types"""
        assert _get_result("isinstance('a', str)") == "True"

    def test_isinstance_str_false(self) -> None:
        assert _get_result("isinstance(1, str)") == "False"

    def test_isinstance_tuple_argument(self) -> None:
        """obj just has to be an instance of ANY class/type on the right"""
        assert _get_result("isinstance(1, (str, int))") == "True"

    def test_isinstance_type_false2(self) -> None:
        assert (
            _get_result(
                """
        isinstance(1, type)
        """
            )
            == "False"
        )

    def test_isinstance_object_true2(self) -> None:
        assert (
            _get_result(
                """
        class Bar(type):
            pass
        mainbar = Bar("Bar", tuple(), {})
        isinstance(mainbar, object)
        """
            )
            == "True"
        )

    def test_isinstance_type_true(self) -> None:
        assert (
            _get_result(
                """
        class Bar(type):
            pass
        mainbar = Bar("Bar", tuple(), {})
        isinstance(mainbar, type)
        """
            )
            == "True"
        )

    def test_isinstance_edge_case(self) -> None:
        """isinstance allows bad type short-circuting"""
        assert _get_result("isinstance(1, (int, 1))") == "True"

    def test_uninferable_bad_type(self) -> None:
        """The second argument must be a class or a tuple of classes"""
        with pytest.raises(InferenceError):
            _get_result_node("isinstance(int, 1)")

    def test_uninferable_keywords(self) -> None:
        """isinstance does not allow keywords"""
        with pytest.raises(InferenceError):
            _get_result_node("isinstance(1, class_or_tuple=int)")

    def test_too_many_args(self) -> None:
        """isinstance must have two arguments"""
        with pytest.raises(InferenceError):
            _get_result_node("isinstance(1, int, str)")

    def test_first_param_is_uninferable(self) -> None:
        with pytest.raises(InferenceError):
            _get_result_node("isinstance(something, int)")


class TestIssubclassBrain:
    """Test issubclass() builtin inference"""

    def test_type_type(self) -> None:
        assert _get_result("issubclass(type, type)") == "True"

    def test_object_type(self) -> None:
        assert _get_result("issubclass(object, type)") == "False"

    def test_type_object(self) -> None:
        assert _get_result("issubclass(type, object)") == "True"

    def test_issubclass_same_class(self) -> None:
        assert _get_result("issubclass(int, int)") == "True"

    def test_issubclass_not_the_same_class(self) -> None:
        assert _get_result("issubclass(str, int)") == "False"

    def test_issubclass_object_true(self) -> None:
        assert (
            _get_result(
                """
        class Bar(object):
            pass
        issubclass(Bar, object)
        """
            )
            == "True"
        )

    def test_issubclass_same_user_defined_class(self) -> None:
        assert (
            _get_result(
                """
        class Bar(object):
            pass
        issubclass(Bar, Bar)
        """
            )
            == "True"
        )

    def test_issubclass_different_user_defined_classes(self) -> None:
        assert (
            _get_result(
                """
        class Foo(object):
            pass
        class Bar(object):
            pass
        issubclass(Bar, Foo)
        """
            )
            == "False"
        )

    def test_issubclass_type_false(self) -> None:
        assert (
            _get_result(
                """
        class Bar(object):
            pass
        issubclass(Bar, type)
        """
            )
            == "False"
        )

    def test_isinstance_tuple_argument(self) -> None:
        """obj just has to be a subclass of ANY class/type on the right"""
        assert _get_result("issubclass(int, (str, int))") == "True"

    def test_isinstance_object_true2(self) -> None:
        assert (
            _get_result(
                """
        class Bar(type):
            pass
        issubclass(Bar, object)
        """
            )
            == "True"
        )

    def test_issubclass_short_circuit(self) -> None:
        """issubclasss allows bad type short-circuting"""
        assert _get_result("issubclass(int, (int, 1))") == "True"

    def test_uninferable_bad_type(self) -> None:
        """The second argument must be a class or a tuple of classes"""
        # Should I subclass
        with pytest.raises(InferenceError):
            _get_result_node("issubclass(int, 1)")

    def test_uninferable_keywords(self) -> None:
        """issubclass does not allow keywords"""
        with pytest.raises(InferenceError):
            _get_result_node("issubclass(int, class_or_tuple=int)")

    def test_too_many_args(self) -> None:
        """issubclass must have two arguments"""
        with pytest.raises(InferenceError):
            _get_result_node("issubclass(int, int, str)")


def _get_result_node(code: str) -> Const:
    node = next(astroid.extract_node(code).infer())
    return node


def _get_result(code: str) -> str:
    return _get_result_node(code).as_string()


class TestLenBuiltinInference:
    def test_len_list(self) -> None:
        # Uses .elts
        node = astroid.extract_node(
            """
        len(['a','b','c'])
        """
        )
        node = next(node.infer())
        assert node.as_string() == "3"
        assert isinstance(node, nodes.Const)

    def test_len_tuple(self) -> None:
        node = astroid.extract_node(
            """
        len(('a','b','c'))
        """
        )
        node = next(node.infer())
        assert node.as_string() == "3"

    def test_len_var(self) -> None:
        # Make sure argument is inferred
        node = astroid.extract_node(
            """
        a = [1,2,'a','b','c']
        len(a)
        """
        )
        node = next(node.infer())
        assert node.as_string() == "5"

    def test_len_dict(self) -> None:
        # Uses .items
        node = astroid.extract_node(
            """
        a = {'a': 1, 'b': 2}
        len(a)
        """
        )
        node = next(node.infer())
        assert node.as_string() == "2"

    def test_len_set(self) -> None:
        node = astroid.extract_node(
            """
        len({'a'})
        """
        )
        inferred_node = next(node.infer())
        assert inferred_node.as_string() == "1"

    def test_len_object(self) -> None:
        """Test len with objects that implement the len protocol"""
        node = astroid.extract_node(
            """
        class A:
            def __len__(self):
                return 57
        len(A())
        """
        )
        inferred_node = next(node.infer())
        assert inferred_node.as_string() == "57"

    def test_len_class_with_metaclass(self) -> None:
        """Make sure proper len method is located"""
        cls_node, inst_node = astroid.extract_node(
            """
        class F2(type):
            def __new__(cls, name, bases, attrs):
                return super().__new__(cls, name, bases, {})
            def __len__(self):
                return 57
        class F(metaclass=F2):
            def __len__(self):
                return 4
        len(F) #@
        len(F()) #@
        """
        )
        assert next(cls_node.infer()).as_string() == "57"
        assert next(inst_node.infer()).as_string() == "4"

    def test_len_object_failure(self) -> None:
        """If taking the length of a class, do not use an instance method"""
        node = astroid.extract_node(
            """
        class F:
            def __len__(self):
                return 57
        len(F)
        """
        )
        with pytest.raises(InferenceError):
            next(node.infer())

    def test_len_string(self) -> None:
        node = astroid.extract_node(
            """
        len("uwu")
        """
        )
        assert next(node.infer()).as_string() == "3"

    def test_len_generator_failure(self) -> None:
        node = astroid.extract_node(
            """
        def gen():
            yield 'a'
            yield 'b'
        len(gen())
        """
        )
        with pytest.raises(InferenceError):
            next(node.infer())

    def test_len_failure_missing_variable(self) -> None:
        node = astroid.extract_node(
            """
        len(a)
        """
        )
        with pytest.raises(InferenceError):
            next(node.infer())

    def test_len_bytes(self) -> None:
        node = astroid.extract_node(
            """
        len(b'uwu')
        """
        )
        assert next(node.infer()).as_string() == "3"

    def test_int_subclass_result(self) -> None:
        """Check that a subclass of an int can still be inferred

        This test does not properly infer the value passed to the
        int subclass (5) but still returns a proper integer as we
        fake the result of the `len()` call.
        """
        node = astroid.extract_node(
            """
        class IntSubclass(int):
            pass

        class F:
            def __len__(self):
                return IntSubclass(5)
        len(F())
        """
        )
        assert next(node.infer()).as_string() == "0"

    @pytest.mark.xfail(reason="Can't use list special astroid fields")
    def test_int_subclass_argument(self):
        """I am unable to access the length of an object which
        subclasses list"""
        node = astroid.extract_node(
            """
        class ListSubclass(list):
            pass
        len(ListSubclass([1,2,3,4,4]))
        """
        )
        assert next(node.infer()).as_string() == "5"

    def test_len_builtin_inference_attribute_error_str(self) -> None:
        """Make sure len builtin doesn't raise an AttributeError
        on instances of str or bytes

        See https://github.com/pylint-dev/pylint/issues/1942
        """
        code = 'len(str("F"))'
        try:
            next(astroid.extract_node(code).infer())
        except InferenceError:
            pass

    def test_len_builtin_inference_recursion_error_self_referential_attribute(
        self,
    ) -> None:
        """Make sure len calls do not trigger
        recursion errors for self referential assignment

        See https://github.com/pylint-dev/pylint/issues/2734
        """
        code = """
        class Data:
            def __init__(self):
                self.shape = []

        data = Data()
        data.shape = len(data.shape)
        data.shape #@
        """
        try:
            astroid.extract_node(code).inferred()
        except RecursionError:
            pytest.fail("Inference call should not trigger a recursion error")


def test_infer_str() -> None:
    ast_nodes = astroid.extract_node(
        """
    str(s) #@
    str('a') #@
    str(some_object()) #@
    """
    )
    for node in ast_nodes:
        inferred = next(node.infer())
        assert isinstance(inferred, astroid.Const)

    node = astroid.extract_node(
        """
    str(s='') #@
    """
    )
    inferred = next(node.infer())
    assert isinstance(inferred, astroid.Instance)
    assert inferred.qname() == "builtins.str"


def test_infer_int() -> None:
    ast_nodes = astroid.extract_node(
        """
    int(0) #@
    int('1') #@
    """
    )
    for node in ast_nodes:
        inferred = next(node.infer())
        assert isinstance(inferred, astroid.Const)

    ast_nodes = astroid.extract_node(
        """
    int(s='') #@
    int('2.5') #@
    int('something else') #@
    int(unknown) #@
    int(b'a') #@
    """
    )
    for node in ast_nodes:
        inferred = next(node.infer())
        assert isinstance(inferred, astroid.Instance)
        assert inferred.qname() == "builtins.int"


def test_infer_dict_from_keys() -> None:
    bad_nodes = astroid.extract_node(
        """
    dict.fromkeys() #@
    dict.fromkeys(1, 2, 3) #@
    dict.fromkeys(a=1) #@
    """
    )
    for node in bad_nodes:
        with pytest.raises(InferenceError):
            next(node.infer())

    # Test uninferable values
    good_nodes = astroid.extract_node(
        """
    from unknown import Unknown
    dict.fromkeys(some_value) #@
    dict.fromkeys(some_other_value) #@
    dict.fromkeys([Unknown(), Unknown()]) #@
    dict.fromkeys([Unknown(), Unknown()]) #@
    """
    )
    for node in good_nodes:
        inferred = next(node.infer())
        assert isinstance(inferred, astroid.Dict)
        assert inferred.items == []

    # Test inferable values

    # from a dictionary's keys
    from_dict = astroid.extract_node(
        """
    dict.fromkeys({'a':2, 'b': 3, 'c': 3}) #@
    """
    )
    inferred = next(from_dict.infer())
    assert isinstance(inferred, astroid.Dict)
    itered = inferred.itered()
    assert all(isinstance(elem, astroid.Const) for elem in itered)
    actual_values = [elem.value for elem in itered]
    assert sorted(actual_values) == ["a", "b", "c"]

    # from a string
    from_string = astroid.extract_node(
        """
    dict.fromkeys('abc')
    """
    )
    inferred = next(from_string.infer())
    assert isinstance(inferred, astroid.Dict)
    itered = inferred.itered()
    assert all(isinstance(elem, astroid.Const) for elem in itered)
    actual_values = [elem.value for elem in itered]
    assert sorted(actual_values) == ["a", "b", "c"]

    # from bytes
    from_bytes = astroid.extract_node(
        """
    dict.fromkeys(b'abc')
    """
    )
    inferred = next(from_bytes.infer())
    assert isinstance(inferred, astroid.Dict)
    itered = inferred.itered()
    assert all(isinstance(elem, astroid.Const) for elem in itered)
    actual_values = [elem.value for elem in itered]
    assert sorted(actual_values) == [97, 98, 99]

    # From list/set/tuple
    from_others = astroid.extract_node(
        """
    dict.fromkeys(('a', 'b', 'c')) #@
    dict.fromkeys(['a', 'b', 'c']) #@
    dict.fromkeys({'a', 'b', 'c'}) #@
    """
    )
    for node in from_others:
        inferred = next(node.infer())
        assert isinstance(inferred, astroid.Dict)
        itered = inferred.itered()
        assert all(isinstance(elem, astroid.Const) for elem in itered)
        actual_values = [elem.value for elem in itered]
        assert sorted(actual_values) == ["a", "b", "c"]


class TestFunctoolsPartial:
    @staticmethod
    def test_infer_partial() -> None:
        ast_node = astroid.extract_node(
            """
        from functools import partial
        def test(a, b):
            '''Docstring'''
            return a + b
        partial(test, 1)(3) #@
        """
        )
        assert isinstance(ast_node.func, nodes.Call)
        inferred = ast_node.func.inferred()
        assert len(inferred) == 1
        partial = inferred[0]
        assert isinstance(partial, objects.PartialFunction)
        assert isinstance(partial.as_string(), str)
        assert isinstance(partial.doc_node, nodes.Const)
        assert partial.doc_node.value == "Docstring"
        assert partial.lineno == 3
        assert partial.col_offset == 0

    def test_invalid_functools_partial_calls(self) -> None:
        ast_nodes = astroid.extract_node(
            """
        from functools import partial
        from unknown import Unknown

        def test(a, b, c):
            return a + b + c

        partial() #@
        partial(test) #@
        partial(func=test) #@
        partial(some_func, a=1) #@
        partial(Unknown, a=1) #@
        partial(2, a=1) #@
        partial(test, unknown=1) #@
        """
        )
        for node in ast_nodes:
            inferred = next(node.infer())
            assert isinstance(inferred, (astroid.FunctionDef, astroid.Instance))
            assert inferred.qname() in {
                "functools.partial",
                "functools.partial.newfunc",
            }

    def test_inferred_partial_function_calls(self) -> None:
        ast_nodes = astroid.extract_node(
            """
        from functools import partial
        def test(a, b):
            return a + b
        partial(test, 1)(3) #@
        partial(test, b=4)(3) #@
        partial(test, b=4)(a=3) #@
        def other_test(a, b, *, c=1):
            return (a + b) * c

        partial(other_test, 1, 2)() #@
        partial(other_test, 1, 2)(c=4) #@
        partial(other_test, c=4)(1, 3) #@
        partial(other_test, 4, c=4)(4) #@
        partial(other_test, 4, c=4)(b=5) #@
        test(1, 2) #@
        partial(other_test, 1, 2)(c=3) #@
        partial(test, b=4)(a=3) #@
        """
        )
        expected_values = [4, 7, 7, 3, 12, 16, 32, 36, 3, 9, 7]
        for node, expected_value in zip(ast_nodes, expected_values):
            inferred = next(node.infer())
            assert isinstance(inferred, astroid.Const)
            assert inferred.value == expected_value

    def test_partial_assignment(self) -> None:
        """Make sure partials are not assigned to original scope."""
        ast_nodes = astroid.extract_node(
            """
        from functools import partial
        def test(a, b): #@
            return a + b
        test2 = partial(test, 1)
        test2 #@
        def test3_scope(a):
            test3 = partial(test, a)
            test3 #@
        """
        )
        func1, func2, func3 = ast_nodes
        assert func1.parent.scope() == func2.parent.scope()
        assert func1.parent.scope() != func3.parent.scope()
        partial_func3 = next(func3.infer())
        # use scope of parent, so that it doesn't just refer to self
        scope = partial_func3.parent.scope()
        assert scope.name == "test3_scope", "parented by closure"

    def test_partial_does_not_affect_scope(self) -> None:
        """Make sure partials are not automatically assigned."""
        ast_nodes = astroid.extract_node(
            """
        from functools import partial
        def test(a, b):
            return a + b
        def scope():
            test2 = partial(test, 1)
            test2 #@
        """
        )
        test2 = next(ast_nodes.infer())
        mod_scope = test2.root()
        scope = test2.parent.scope()
        assert set(mod_scope) == {"test", "scope", "partial"}
        assert set(scope) == {"test2"}

    def test_multiple_partial_args(self) -> None:
        "Make sure partials remember locked-in args."
        ast_node = astroid.extract_node(
            """
        from functools import partial
        def test(a, b, c, d, e=5):
            return a + b + c + d + e
        test1 = partial(test, 1)
        test2 = partial(test1, 2)
        test3 = partial(test2, 3)
        test3(4, e=6) #@
        """
        )
        expected_args = [1, 2, 3, 4]
        expected_keywords = {"e": 6}

        call_site = astroid.arguments.CallSite.from_call(ast_node)
        called_func = next(ast_node.func.infer())
        called_args = called_func.filled_args + call_site.positional_arguments
        called_keywords = {**called_func.filled_keywords, **call_site.keyword_arguments}
        assert len(called_args) == len(expected_args)
        assert [arg.value for arg in called_args] == expected_args
        assert len(called_keywords) == len(expected_keywords)

        for keyword, value in expected_keywords.items():
            assert keyword in called_keywords
            assert called_keywords[keyword].value == value


def test_http_client_brain() -> None:
    node = astroid.extract_node(
        """
    from http.client import OK
    OK
    """
    )
    inferred = next(node.infer())
    assert isinstance(inferred, astroid.Instance)


def test_http_status_brain() -> None:
    node = astroid.extract_node(
        """
    import http
    http.HTTPStatus.CONTINUE.phrase
    """
    )
    inferred = next(node.infer())
    # Cannot infer the exact value but the field is there.
    assert inferred.value == ""

    node = astroid.extract_node(
        """
    import http
    http.HTTPStatus(200).phrase
    """
    )
    inferred = next(node.infer())
    assert isinstance(inferred, astroid.Const)


def test_http_status_brain_iterable() -> None:
    """Astroid inference of `http.HTTPStatus` is an iterable subclass of `enum.IntEnum`"""
    node = astroid.extract_node(
        """
    import http
    http.HTTPStatus
    """
    )
    inferred = next(node.infer())
    assert "enum.IntEnum" in [ancestor.qname() for ancestor in inferred.ancestors()]
    assert inferred.getattr("__iter__")


def test_oserror_model() -> None:
    node = astroid.extract_node(
        """
    try:
        1/0
    except OSError as exc:
        exc #@
    """
    )
    inferred = next(node.infer())
    strerror = next(inferred.igetattr("strerror"))
    assert isinstance(strerror, astroid.Const)
    assert strerror.value == ""


@pytest.mark.skipif(PY313_PLUS, reason="Python >= 3.13 no longer has a crypt module")
def test_crypt_brain() -> None:
    module = MANAGER.ast_from_module_name("crypt")
    dynamic_attrs = [
        "METHOD_SHA512",
        "METHOD_SHA256",
        "METHOD_BLOWFISH",
        "METHOD_MD5",
        "METHOD_CRYPT",
    ]
    for attr in dynamic_attrs:
        assert attr in module


@pytest.mark.parametrize(
    "code,expected_class,expected_value",
    [
        ("'hey'.encode()", astroid.Const, b""),
        ("b'hey'.decode()", astroid.Const, ""),
        ("'hey'.encode().decode()", astroid.Const, ""),
    ],
)
def test_str_and_bytes(code, expected_class, expected_value):
    node = astroid.extract_node(code)
    inferred = next(node.infer())
    assert isinstance(inferred, expected_class)
    assert inferred.value == expected_value


def test_no_recursionerror_on_self_referential_length_check() -> None:
    """
    Regression test for https://github.com/pylint-dev/astroid/issues/777

    This test should only raise an InferenceError and no RecursionError.
    """
    with pytest.raises(InferenceError):
        node = astroid.extract_node(
            """
        class Crash:
            def __len__(self) -> int:
                return len(self)
        len(Crash()) #@
        """
        )
        assert isinstance(node, nodes.NodeNG)
        node.inferred()


def test_inference_on_outer_referential_length_check() -> None:
    """
    Regression test for https://github.com/pylint-dev/pylint/issues/5244
    See also https://github.com/pylint-dev/astroid/pull/1234

    This test should succeed without any error.
    """
    node = astroid.extract_node(
        """
    class A:
        def __len__(self) -> int:
            return 42

    class Crash:
        def __len__(self) -> int:
            a = A()
            return len(a)

    len(Crash()) #@
    """
    )
    inferred = node.inferred()
    assert len(inferred) == 1
    assert isinstance(inferred[0], nodes.Const)
    assert inferred[0].value == 42


def test_no_attributeerror_on_self_referential_length_check() -> None:
    """
    Regression test for https://github.com/pylint-dev/pylint/issues/5244
    See also https://github.com/pylint-dev/astroid/pull/1234

    This test should only raise an InferenceError and no AttributeError.
    """
    with pytest.raises(InferenceError):
        node = astroid.extract_node(
            """
        class MyClass:
            def some_func(self):
                return lambda: 42

            def __len__(self):
                return len(self.some_func())

        len(MyClass()) #@
        """
        )
        assert isinstance(node, nodes.NodeNG)
        node.inferred()
