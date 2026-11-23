# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import io
import re
import sys
import unittest
from unittest.mock import patch

import pytest

import astroid
from astroid import MANAGER, builder, nodes, test_utils, util
from astroid.bases import Instance
from astroid.brain.brain_namedtuple_enum import _get_namedtuple_fields
from astroid.const import PY312_PLUS, PY313_PLUS, PY315_PLUS
from astroid.exceptions import (
    AttributeInferenceError,
    InferenceError,
    UseInferenceDefault,
)


def assertEqualMro(klass: nodes.ClassDef, expected_mro: list[str]) -> None:
    """Check mro names."""
    assert [member.qname() for member in klass.mro()] == expected_mro


class CollectionsDequeTests(unittest.TestCase):
    def _inferred_queue_instance(self) -> Instance:
        node = builder.extract_node("""
        import collections
        q = collections.deque([])
        q
        """)
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
        node = builder.extract_node("""
        import collections
        d = collections.OrderedDict()
        d
        """)
        return next(node.infer())

    def test_ordered_dict_py34method(self) -> None:
        inferred = self._inferred_ordered_dict_instance()
        self.assertIn("move_to_end", inferred.locals)


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
            node = astroid.extract_node(f"""
            import sys
            sys.{name}
            """)
            inferred = next(node.infer())
            buffer_attr = next(inferred.igetattr("buffer"))
            self.assertIsInstance(buffer_attr, astroid.Instance)
            self.assertEqual(buffer_attr.name, "BufferedWriter")
            raw = next(buffer_attr.igetattr("raw"))
            self.assertIsInstance(raw, astroid.Instance)
            self.assertEqual(raw.name, "FileIO")


def check_metaclass_is_abc(node: nodes.ClassDef):
    if PY312_PLUS and node.name == "ByteString":
        # .metaclass() finds the first metaclass in the mro(),
        # which, from 3.12, is _DeprecateByteStringMeta (unhelpful)
        # until ByteString is removed in 3.17.
        # Jump over the first two ByteString classes in the mro().
        check_metaclass_is_abc(node.mro()[2])
    else:
        meta = node.metaclass()
        assert isinstance(meta, nodes.ClassDef)
        assert meta.name == "ABCMeta"


class CollectionsBrain(unittest.TestCase):
    def test_collections_abc_is_importable(self) -> None:
        """
        Test that we can import `collections.abc`.

        The collections.abc has gone through various formats of being frozen. Therefore, we ensure
        that we can still import it (correctly).
        """
        import_node = builder.extract_node("import collections.abc")
        assert isinstance(import_node, nodes.Import)
        imported_module = import_node.do_import_module(import_node.names[0][0])
        # Make sure that the file we have imported is actually the submodule of collections and
        # not the `abc` module. (Which would happen if you call `importlib.util.find_spec("abc")`
        # instead of `importlib.util.find_spec("collections.abc")`)
        assert isinstance(imported_module.file, str)
        assert "collections" in imported_module.file

    def test_collections_object_not_subscriptable(self) -> None:
        """
        Test that unsubscriptable types are detected
        Hashable is not subscriptable even with python39
        """
        wrong_node = builder.extract_node("""
        import collections.abc
        collections.abc.Hashable[int]
        """)
        with self.assertRaises(InferenceError):
            next(wrong_node.infer())
        right_node = builder.extract_node("""
        import collections.abc
        collections.abc.Hashable
        """)
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
        right_node = builder.extract_node("""
        import collections.abc
        collections.abc.MutableSet[int]
        """)
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

    def test_collections_object_subscriptable_2(self):
        """Starting with python39 Iterator in the collection.abc module is subscriptable"""
        node = builder.extract_node("""
        import collections.abc
        class Derived(collections.abc.Iterator[int]):
            pass
        """)
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

    def test_collections_object_subscriptable_3(self):
        """With Python 3.9 the ByteString class of the collections module is subscriptable
        (but not the same class from typing module)"""
        right_node = builder.extract_node("""
        import collections.abc
        collections.abc.ByteString[int]
        """)
        inferred = next(right_node.infer())
        check_metaclass_is_abc(inferred)
        self.assertIsInstance(
            inferred.getattr("__class_getitem__")[0], nodes.FunctionDef
        )


class TypingBrain(unittest.TestCase):
    def test_namedtuple_base(self) -> None:
        klass = builder.extract_node("""
        from typing import NamedTuple

        class X(NamedTuple("X", [("a", int), ("b", str), ("c", bytes)])):
           pass
        """)
        self.assertEqual(
            [ancestor.name for ancestor in klass.ancestors()], ["X", "tuple", "object"]
        )
        for ancestor in klass.ancestors():
            self.assertFalse(ancestor.parent is None)

    def test_namedtuple_api_on_self(self) -> None:
        """``self`` in a method has the namedtuple API and the tuple methods.

        https://github.com/pylint-dev/pylint/issues/7891
        """
        klass, *attributes = builder.extract_node("""
        from typing import NamedTuple

        class X(NamedTuple): #@
            a: int
            b: str = "b"

            def method(self):
                self._asdict() #@
                self._replace(a=1) #@
                self._fields #@
                self._make([1, "b"]) #@
                type(self)._make([1, "b"]) #@
                self._field_defaults #@
                self.count #@
                self.index #@
        """)
        asdict, replace, fields, make, type_make, field_defaults, count, index = (
            next(attribute.infer()) for attribute in attributes
        )
        # pylint recognizes a typing.NamedTuple subclass by this ancestor.
        assert [ancestor.qname() for ancestor in klass.ancestors()] == [
            "typing.NamedTuple",
            "builtins.tuple",
            "builtins.object",
        ]
        assert isinstance(replace, astroid.Instance)
        assert replace._proxied is klass
        for made in (make, type_make):
            assert isinstance(made, astroid.Instance)
            assert made.name == "X"
        # Instances, not ``()`` or ``{}``: the items are not known.
        assert isinstance(asdict, astroid.Instance)
        assert asdict.pytype() == "builtins.dict"
        assert isinstance(fields, astroid.Instance)
        assert fields.pytype() == "builtins.tuple"
        assert isinstance(field_defaults, astroid.Instance)
        assert field_defaults.pytype() == "builtins.dict"
        for method, name in ((count, "count"), (index, "index")):
            assert isinstance(method, astroid.BoundMethod)
            assert method.name == name
            assert method.parent.qname() == "builtins.tuple"

    def test_namedtuple_inference(self) -> None:
        klass = builder.extract_node("""
        from typing import NamedTuple

        class X(NamedTuple("X", [("a", int), ("b", str), ("c", bytes)])):
           pass
        """)
        base = next(base for base in klass.ancestors() if base.name == "X")
        self.assertSetEqual({"a", "b", "c"}, set(base.instance_attrs))

    def test_namedtuple_instance_attrs(self) -> None:
        result = builder.extract_node("""
        from typing import NamedTuple
        NamedTuple("A", [("a", int), ("b", str), ("c", bytes)])(1, 2, 3) #@
        """)
        inferred = next(result.infer())
        for name, attr in inferred.instance_attrs.items():
            self.assertEqual(attr[0].attrname, name)

    def test_namedtuple_simple(self) -> None:
        result = builder.extract_node("""
        from typing import NamedTuple
        NamedTuple("A", [("a", int), ("b", str), ("c", bytes)])
        """)
        inferred = next(result.infer())
        self.assertIsInstance(inferred, nodes.ClassDef)
        self.assertSetEqual({"a", "b", "c"}, set(inferred.instance_attrs))

    def test_namedtuple_uninferable_member(self) -> None:
        call = builder.extract_node("""
        from typing import namedtuple
        namedtuple('uninf', {x: x for x in range(0)})  #@""")
        with pytest.raises(UseInferenceDefault):
            _get_namedtuple_fields(call)

        call = builder.extract_node("""
        from typing import namedtuple
        uninferable = {x: x for x in range(0)}
        namedtuple('uninferable', uninferable)  #@
        """)
        with pytest.raises(UseInferenceDefault):
            _get_namedtuple_fields(call)

    def test_typing_type_without_tip(self):
        """Regression test for https://github.com/pylint-dev/pylint/issues/5770"""
        node = builder.extract_node("""
        from typing import NewType

        def make_new_type(t):
            new_type = NewType(f'IntRange_{t}', t) #@
        """)
        with self.assertRaises(UseInferenceDefault):
            astroid.brain.brain_typing.infer_typing_typevar_or_newtype(node.value)

    def test_namedtuple_class_form_assignment_targets(self):
        """An assignment in the body may not bind a single plain name.

        Regression test for https://github.com/pylint-dev/astroid/issues/3190
        """
        attribute, subscript, unpacking = builder.extract_node("""
        from typing import NamedTuple

        class Attribute(NamedTuple):
            cat.color = "black"

        class Subscript(NamedTuple):
            basket[0] = "apple"

        class Unpacking(NamedTuple):
            apple, banana = "red", "yellow"

        Attribute()  #@
        Subscript()  #@
        Unpacking()  #@
        """)
        # Inference must not raise ``AttributeError`` or ``KeyError``.
        for node in (attribute, subscript, unpacking):
            self.assertIsInstance(next(node.infer()), astroid.Instance)

        # The names bound by unpacking are still class attributes.
        inferred = next(unpacking.infer())
        for name, value in (("apple", "red"), ("banana", "yellow")):
            self.assertEqual(next(inferred.getattr(name)[0].infer()).value, value)

    @test_utils.require_version(minver="3.12")
    def test_typing_generic_subscriptable_pep695(self):
        """Test class using type parameters is subscriptable with __class_getitem__ (added in PY312)"""
        node = builder.extract_node("""
        class Foo[T]: ...
        class Bar[T](Foo[T]): ...
        """)
        inferred = next(node.infer())
        assert isinstance(inferred, nodes.ClassDef)
        assert inferred.name == "Bar"
        assert isinstance(inferred.getattr("__class_getitem__")[0], nodes.FunctionDef)
        ancestors = list(inferred.ancestors())
        assert len(ancestors) == 2
        assert ancestors[0].name == "Foo"
        assert ancestors[1].name == "object"

    def test_typed_dict_required_and_optional_keys(self):
        """TypedDict subclasses expose ``__required_keys__`` and ``__optional_keys__``."""
        cls = builder.extract_node("""
        from typing import TypedDict

        class CustomTD(TypedDict):  #@
            var: int
        """)
        for attr in ("__required_keys__", "__optional_keys__"):
            assert cls.getattr(attr), f"{cls.name}.{attr} not found"

    def test_typing_object_notsubscriptable_3(self):
        """The ByteString class of the typing module is not
        subscriptable (whereas it is in the collections' module)"""
        right_node = builder.extract_node("""
        import typing
        typing.ByteString
        """)
        inferred = next(right_node.infer())
        # From Python 3.15 we add a stub definition of `ByteString`. It doesn't need all properties
        # of the original implementation.
        if not PY315_PLUS:
            check_metaclass_is_abc(inferred)
        with self.assertRaises(AttributeInferenceError):
            self.assertIsInstance(
                inferred.getattr("__class_getitem__")[0], nodes.FunctionDef
            )


class ReBrainTest(unittest.TestCase):
    def test_regex_flags(self) -> None:
        names = [name for name in dir(re) if name.isupper()]
        re_ast = MANAGER.ast_from_module_name("re")
        for name in names:
            self.assertIn(name, re_ast)
            self.assertEqual(next(re_ast[name].infer()).value, getattr(re, name))


class RandomSampleTest(unittest.TestCase):
    def test_inferred_successfully(self) -> None:
        node = astroid.extract_node("""
        import random
        random.sample([1, 2], 2) #@
        """)
        inferred = next(node.infer())
        self.assertIsInstance(inferred, nodes.List)
        elems = sorted(elem.value for elem in inferred.elts)
        self.assertEqual(elems, [1, 2])

    def test_arguments_inferred_successfully(self) -> None:
        """Test inference of `random.sample` when both arguments are of type `nodes.Call`."""
        node = astroid.extract_node("""
        import random

        def sequence():
            return [1, 2]

        random.sample(sequence(), len([1,2])) #@
        """)
        # Check that arguments are of type `nodes.Call`.
        sequence, length = node.args
        self.assertIsInstance(sequence, nodes.Call)
        self.assertIsInstance(length, nodes.Call)

        # Check the inference of `random.sample` call.
        inferred = next(node.infer())
        self.assertIsInstance(inferred, nodes.List)
        elems = sorted(elem.value for elem in inferred.elts)
        self.assertEqual(elems, [1, 2])


class SubprocessTest(unittest.TestCase):
    """Test subprocess brain"""

    def test_popen_does_not_have_class_getitem(self):
        code = """import subprocess; subprocess.Popen"""
        node = astroid.extract_node(code)
        inferred = next(node.infer())
        assert "__class_getitem__" in inferred


def _get_result_node(code: str) -> nodes.Const:
    node = next(astroid.extract_node(code).infer())
    return node


def _get_result(code: str) -> str:
    return _get_result_node(code).as_string()


class TestLenBuiltinInference:

    @pytest.mark.xfail(reason="Can't use list special astroid fields")
    def test_int_subclass_argument(self):
        """I am unable to access the length of an object which
        subclasses list"""
        node = astroid.extract_node("""
        class ListSubclass(list):
            pass
        len(ListSubclass([1,2,3,4,4]))
        """)
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


def test_infer_str_const() -> None:
    ast_nodes = astroid.extract_node("""
    str('') #@
    str('a') #@
    str(1) #@
    str(True) #@
    str(False) #@
    str(None) #@
    str(4.33) #@
    str(...) #@
    str(2 + 2) #@
    str() #@
    str(int) #@
    str(2 if unknown() else 3) #@
    """)

    inferred = list(node.inferred()[0].value for node in ast_nodes)
    assert inferred[0] == ""
    assert inferred[1] == "a"
    assert inferred[2] == "1"
    assert inferred[3] == "True"
    assert inferred[4] == "False"
    assert inferred[5] == "None"
    assert inferred[6] == "4.33"
    assert inferred[7] == "Ellipsis"
    assert inferred[8] == "4"
    assert inferred[9] == ""
    assert inferred[10] == ""
    assert inferred[11] == ""


def test_infer_dict_from_keys() -> None:
    bad_nodes = astroid.extract_node("""
    dict.fromkeys() #@
    dict.fromkeys(1, 2, 3) #@
    dict.fromkeys(a=1) #@
    """)
    for node in bad_nodes:
        with pytest.raises(InferenceError):
            if isinstance(next(node.infer()), util.UninferableBase):
                raise InferenceError

    # Test uninferable values
    good_nodes = astroid.extract_node("""
    from unknown import Unknown
    dict.fromkeys(some_value) #@
    dict.fromkeys(some_other_value) #@
    dict.fromkeys([Unknown(), Unknown()]) #@
    dict.fromkeys([Unknown(), Unknown()]) #@
    dict.fromkeys({(1, 2): 3}) #@
    dict.fromkeys(1) #@
    """)
    for node in good_nodes:
        inferred = next(node.infer())
        assert isinstance(inferred, nodes.Dict)
        assert inferred.items == []

    # Test inferable values

    # from a dictionary's keys
    from_dict = astroid.extract_node("""
    dict.fromkeys({'a':2, 'b': 3, 'c': 3}) #@
    """)
    inferred = next(from_dict.infer())
    assert isinstance(inferred, nodes.Dict)
    itered = inferred.itered()
    assert all(isinstance(elem, nodes.Const) for elem in itered)
    actual_values = [elem.value for elem in itered]
    assert sorted(actual_values) == ["a", "b", "c"]

    # from a string
    from_string = astroid.extract_node("""
    dict.fromkeys('abc')
    """)
    inferred = next(from_string.infer())
    assert isinstance(inferred, nodes.Dict)
    itered = inferred.itered()
    assert all(isinstance(elem, nodes.Const) for elem in itered)
    actual_values = [elem.value for elem in itered]
    assert sorted(actual_values) == ["a", "b", "c"]

    # from bytes
    from_bytes = astroid.extract_node("""
    dict.fromkeys(b'abc')
    """)
    inferred = next(from_bytes.infer())
    assert isinstance(inferred, nodes.Dict)
    itered = inferred.itered()
    assert all(isinstance(elem, nodes.Const) for elem in itered)
    actual_values = [elem.value for elem in itered]
    assert sorted(actual_values) == [97, 98, 99]

    # From list/set/tuple
    from_others = astroid.extract_node("""
    dict.fromkeys(('a', 'b', 'c')) #@
    dict.fromkeys(['a', 'b', 'c']) #@
    dict.fromkeys({'a', 'b', 'c'}) #@
    """)
    for node in from_others:
        inferred = next(node.infer())
        assert isinstance(inferred, nodes.Dict)
        itered = inferred.itered()
        assert all(isinstance(elem, nodes.Const) for elem in itered)
        actual_values = [elem.value for elem in itered]
        assert sorted(actual_values) == ["a", "b", "c"]


def test_container_transform_oversized_str_declines() -> None:
    """list/set/tuple/frozenset must not build one Const per character for a
    str/bytes constant longer than the cap."""
    with patch("astroid.brain.brain_builtin_inference._MAX_INFERABLE_STR_LEN", 4):
        for builtin in ("list", "set", "tuple", "frozenset"):
            node = astroid.extract_node(f'{builtin}("abcdef")')
            inferred = next(node.infer())
            assert isinstance(inferred, Instance)

    # Small strings still infer their exact contents.
    node = astroid.extract_node('list("abc")')
    inferred = next(node.infer())
    assert isinstance(inferred, nodes.List)
    assert [elem.value for elem in inferred.elts] == ["a", "b", "c"]


def test_infer_dict_fromkeys_oversized_str_declines() -> None:
    """dict.fromkeys must not build one key per character for a str/bytes
    constant longer than the cap."""
    with patch("astroid.brain.brain_builtin_inference._MAX_INFERABLE_STR_LEN", 4):
        node = astroid.extract_node('dict.fromkeys("abcdef")')
        inferred = next(node.infer())
        assert isinstance(inferred, nodes.Dict)
        assert inferred.items == []


def test_infer_dict_from_keys_deduplicates() -> None:
    # dict.fromkeys drops duplicate keys, so the inferred dict must too. As a
    # side effect a repeated string no longer materializes one key per
    # character (dict.fromkeys("x" * 10**8) is a single-key dict).
    nodes_with_dupes = astroid.extract_node("""
    dict.fromkeys("aab") #@
    dict.fromkeys(b"aab") #@
    dict.fromkeys([1, 1, 2]) #@
    dict.fromkeys((1, 2, 1)) #@
    """)
    expected = [["a", "b"], [97, 98], [1, 2], [1, 2]]
    for node, keys in zip(nodes_with_dupes, expected):
        inferred = next(node.infer())
        assert isinstance(inferred, nodes.Dict)
        assert [elem.value for elem in inferred.itered()] == keys

    repeated = astroid.extract_node('dict.fromkeys("x" * 1000)')
    inferred = next(repeated.infer())
    assert isinstance(inferred, nodes.Dict)
    assert [elem.value for elem in inferred.itered()] == ["x"]


class TestFunctoolsPartial:

    def test_invalid_functools_partial_calls(self) -> None:
        ast_nodes = astroid.extract_node("""
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
        """)
        for node in ast_nodes:
            inferred = next(node.infer())
            assert isinstance(inferred, (nodes.FunctionDef, astroid.Instance))
            assert inferred.qname() in {
                "functools.partial",
                "functools.partial.newfunc",
            }

    def test_inferred_partial_function_calls(self) -> None:
        ast_nodes = astroid.extract_node("""
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
        """)
        expected_values = [4, 7, 7, 3, 12, 16, 32, 36, 3, 9, 7]
        for node, expected_value in zip(ast_nodes, expected_values):
            inferred = next(node.infer())
            assert isinstance(inferred, nodes.Const)
            assert inferred.value == expected_value

    def test_partial_assignment(self) -> None:
        """Make sure partials are not assigned to original scope."""
        ast_nodes = astroid.extract_node("""
        from functools import partial
        def test(a, b): #@
            return a + b
        test2 = partial(test, 1)
        test2 #@
        def test3_scope(a):
            test3 = partial(test, a)
            test3 #@
        """)
        func1, func2, func3 = ast_nodes
        assert func1.parent.scope() == func2.parent.scope()
        assert func1.parent.scope() != func3.parent.scope()
        partial_func3 = next(func3.infer())
        # use scope of parent, so that it doesn't just refer to self
        scope = partial_func3.parent.scope()
        assert scope.name == "test3_scope", "parented by closure"

    def test_multiple_partial_args(self) -> None:
        "Make sure partials remember locked-in args."
        ast_node = astroid.extract_node("""
        from functools import partial
        def test(a, b, c, d, e=5):
            return a + b + c + d + e
        test1 = partial(test, 1)
        test2 = partial(test1, 2)
        test3 = partial(test2, 3)
        test3(4, e=6) #@
        """)
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
        ("'hey'.encode()", nodes.Const, b""),
        ("b'hey'.decode()", nodes.Const, ""),
        ("'hey'.encode().decode()", nodes.Const, ""),
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
        node = astroid.extract_node("""
        class Crash:
            def __len__(self) -> int:
                return len(self)
        len(Crash()) #@
        """)
        assert isinstance(node, nodes.NodeNG)
        node.inferred()


def test_no_attributeerror_on_self_referential_length_check() -> None:
    """
    Regression test for https://github.com/pylint-dev/pylint/issues/5244
    See also https://github.com/pylint-dev/astroid/pull/1234

    This test should only raise an InferenceError and no AttributeError.
    """
    with pytest.raises(InferenceError):
        node = astroid.extract_node("""
        class MyClass:
            def some_func(self):
                return lambda: 42

            def __len__(self):
                return len(self.some_func())

        len(MyClass()) #@
        """)
        assert isinstance(node, nodes.NodeNG)
        node.inferred()
