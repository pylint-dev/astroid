# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import unittest

import pytest

import astroid
from astroid import bases, builder, nodes, objects
from astroid.exceptions import InferenceError


class EnumBrainTest(unittest.TestCase):
    def test_simple_enum(self) -> None:
        module = builder.parse(
            """
        import enum

        class MyEnum(enum.Enum):
            one = "one"
            two = "two"

            def mymethod(self, x):
                return 5

        """
        )

        enumeration = next(module["MyEnum"].infer())
        one = enumeration["one"]
        self.assertEqual(one.pytype(), ".MyEnum.one")

        for propname in ("name", "value"):
            prop = next(iter(one.getattr(propname)))
            self.assertIn("builtins.property", prop.decoratornames())

        meth = one.getattr("mymethod")[0]
        self.assertIsInstance(meth, astroid.FunctionDef)

    def test_looks_like_enum_false_positive(self) -> None:
        # Test that a class named Enumeration is not considered a builtin enum.
        module = builder.parse(
            """
        class Enumeration(object):
            def __init__(self, name, enum_list):
                pass
            test = 42
        """
        )
        enumeration = module["Enumeration"]
        test = next(enumeration.igetattr("test"))
        self.assertEqual(test.value, 42)

    def test_user_enum_false_positive(self) -> None:
        # Test that a user-defined class named Enum is not considered a builtin enum.
        ast_node = astroid.extract_node(
            """
        class Enum:
            pass

        class Color(Enum):
            red = 1

        Color.red #@
        """
        )
        assert isinstance(ast_node, nodes.NodeNG)
        inferred = ast_node.inferred()
        self.assertEqual(len(inferred), 1)
        self.assertIsInstance(inferred[0], astroid.Const)
        self.assertEqual(inferred[0].value, 1)

    def test_ignores_with_nodes_from_body_of_enum(self) -> None:
        code = """
        import enum

        class Error(enum.Enum):
            Foo = "foo"
            Bar = "bar"
            with "error" as err:
                pass
        """
        node = builder.extract_node(code)
        inferred = next(node.infer())
        assert "err" in inferred.locals
        assert len(inferred.locals["err"]) == 1

    def test_enum_multiple_base_classes(self) -> None:
        module = builder.parse(
            """
        import enum

        class Mixin:
            pass

        class MyEnum(Mixin, enum.Enum):
            one = 1
        """
        )
        enumeration = next(module["MyEnum"].infer())
        one = enumeration["one"]

        clazz = one.getattr("__class__")[0]
        self.assertTrue(
            clazz.is_subtype_of(".Mixin"),
            "Enum instance should share base classes with generating class",
        )

    def test_int_enum(self) -> None:
        module = builder.parse(
            """
        import enum

        class MyEnum(enum.IntEnum):
            one = 1
        """
        )

        enumeration = next(module["MyEnum"].infer())
        one = enumeration["one"]

        clazz = one.getattr("__class__")[0]
        self.assertTrue(
            clazz.is_subtype_of("builtins.int"),
            "IntEnum based enums should be a subtype of int",
        )

    def test_enum_func_form_is_class_not_instance(self) -> None:
        cls, instance = builder.extract_node(
            """
        from enum import Enum
        f = Enum('Audience', ['a', 'b', 'c'])
        f #@
        f(1) #@
        """
        )
        inferred_cls = next(cls.infer())
        self.assertIsInstance(inferred_cls, bases.Instance)
        inferred_instance = next(instance.infer())
        self.assertIsInstance(inferred_instance, bases.Instance)
        self.assertIsInstance(next(inferred_instance.igetattr("name")), nodes.Const)
        self.assertIsInstance(next(inferred_instance.igetattr("value")), nodes.Const)

    def test_enum_func_form_iterable(self) -> None:
        instance = builder.extract_node(
            """
        from enum import Enum
        Animal = Enum('Animal', 'ant bee cat dog')
        Animal
        """
        )
        inferred = next(instance.infer())
        self.assertIsInstance(inferred, astroid.Instance)
        self.assertTrue(inferred.getattr("__iter__"))

    def test_enum_func_form_subscriptable(self) -> None:
        instance, name = builder.extract_node(
            """
        from enum import Enum
        Animal = Enum('Animal', 'ant bee cat dog')
        Animal['ant'] #@
        Animal['ant'].name #@
        """
        )
        instance = next(instance.infer())
        self.assertIsInstance(instance, astroid.Instance)

        inferred = next(name.infer())
        self.assertIsInstance(inferred, astroid.Const)

    def test_enum_func_form_has_dunder_members(self) -> None:
        instance = builder.extract_node(
            """
        from enum import Enum
        Animal = Enum('Animal', 'ant bee cat dog')
        for i in Animal.__members__:
            i #@
        """
        )
        instance = next(instance.infer())
        self.assertIsInstance(instance, astroid.Const)
        self.assertIsInstance(instance.value, str)

    def test_infer_enum_value_as_the_right_type(self) -> None:
        string_value, int_value = builder.extract_node(
            """
        from enum import Enum
        class A(Enum):
            a = 'a'
            b = 1
        A.a.value #@
        A.b.value #@
        """
        )
        inferred_string = string_value.inferred()
        assert any(
            isinstance(elem, astroid.Const) and elem.value == "a"
            for elem in inferred_string
        )

        inferred_int = int_value.inferred()
        assert any(
            isinstance(elem, astroid.Const) and elem.value == 1 for elem in inferred_int
        )

    def test_mingled_single_and_double_quotes_does_not_crash(self) -> None:
        node = builder.extract_node(
            """
        from enum import Enum
        class A(Enum):
            a = 'x"y"'
        A.a.value #@
        """
        )
        inferred_string = next(node.infer())
        assert inferred_string.value == 'x"y"'

    def test_special_characters_does_not_crash(self) -> None:
        node = builder.extract_node(
            """
        import enum
        class Example(enum.Enum):
            NULL = '\\N{NULL}'
        Example.NULL.value
        """
        )
        inferred_string = next(node.infer())
        assert inferred_string.value == "\N{NULL}"

    def test_dont_crash_on_for_loops_in_body(self) -> None:
        node = builder.extract_node(
            """

        class Commands(IntEnum):
            _ignore_ = 'Commands index'
            _init_ = 'value string'

            BEL = 0x07, 'Bell'
            Commands = vars()
            for index in range(4):
                Commands[f'DC{index + 1}'] = 0x11 + index, f'Device Control {index + 1}'

        Commands
        """
        )
        inferred = next(node.infer())
        assert isinstance(inferred, astroid.ClassDef)

    def test_enum_tuple_list_values(self) -> None:
        tuple_node, list_node = builder.extract_node(
            """
        import enum

        class MyEnum(enum.Enum):
            a = (1, 2)
            b = [2, 4]
        MyEnum.a.value #@
        MyEnum.b.value #@
        """
        )
        inferred_tuple_node = next(tuple_node.infer())
        inferred_list_node = next(list_node.infer())
        assert isinstance(inferred_tuple_node, astroid.Tuple)
        assert isinstance(inferred_list_node, astroid.List)
        assert inferred_tuple_node.as_string() == "(1, 2)"
        assert inferred_list_node.as_string() == "[2, 4]"

    def test_enum_starred_is_skipped(self) -> None:
        code = """
        from enum import Enum
        class ContentType(Enum):
            TEXT, PHOTO, VIDEO, GIF, YOUTUBE, *_ = [1, 2, 3, 4, 5, 6]
        ContentType.TEXT #@
        """
        node = astroid.extract_node(code)
        next(node.infer())

    def test_enum_name_is_str_on_self(self) -> None:
        code = """
        from enum import Enum
        class TestEnum(Enum):
            def func(self):
                self.name #@
                self.value #@
        TestEnum.name #@
        TestEnum.value #@
        """
        i_name, i_value, c_name, c_value = astroid.extract_node(code)

        # <instance>.name should be a string, <class>.name should be a property (that
        # forwards the lookup to __getattr__)
        inferred = next(i_name.infer())
        assert isinstance(inferred, nodes.Const)
        assert inferred.pytype() == "builtins.str"
        inferred = next(c_name.infer())
        assert isinstance(inferred, objects.Property)

        # Inferring .value should not raise InferenceError. It is probably Uninferable
        # but we don't particularly care
        next(i_value.infer())
        next(c_value.infer())

    def test_enum_name_and_value_members_override_dynamicclassattr(self) -> None:
        code = """
        from enum import Enum
        class TrickyEnum(Enum):
            name = 1
            value = 2

            def func(self):
                self.name #@
                self.value #@
        TrickyEnum.name #@
        TrickyEnum.value #@
        """
        i_name, i_value, c_name, c_value = astroid.extract_node(code)

        # All of these cases should be inferred as enum members
        inferred = next(i_name.infer())
        assert isinstance(inferred, bases.Instance)
        assert inferred.pytype() == ".TrickyEnum.name"
        inferred = next(c_name.infer())
        assert isinstance(inferred, bases.Instance)
        assert inferred.pytype() == ".TrickyEnum.name"
        inferred = next(i_value.infer())
        assert isinstance(inferred, bases.Instance)
        assert inferred.pytype() == ".TrickyEnum.value"
        inferred = next(c_value.infer())
        assert isinstance(inferred, bases.Instance)
        assert inferred.pytype() == ".TrickyEnum.value"

    def test_enum_subclass_member_name(self) -> None:
        ast_node = astroid.extract_node(
            """
        from enum import Enum

        class EnumSubclass(Enum):
            pass

        class Color(EnumSubclass):
            red = 1

        Color.red.name #@
        """
        )
        assert isinstance(ast_node, nodes.NodeNG)
        inferred = ast_node.inferred()
        self.assertEqual(len(inferred), 1)
        self.assertIsInstance(inferred[0], astroid.Const)
        self.assertEqual(inferred[0].value, "red")

    def test_enum_subclass_member_value(self) -> None:
        ast_node = astroid.extract_node(
            """
        from enum import Enum

        class EnumSubclass(Enum):
            pass

        class Color(EnumSubclass):
            red = 1

        Color.red.value #@
        """
        )
        assert isinstance(ast_node, nodes.NodeNG)
        inferred = ast_node.inferred()
        self.assertEqual(len(inferred), 1)
        self.assertIsInstance(inferred[0], astroid.Const)
        self.assertEqual(inferred[0].value, 1)

    def test_enum_subclass_member_method(self) -> None:
        # See Pylint issue #2626
        ast_node = astroid.extract_node(
            """
        from enum import Enum

        class EnumSubclass(Enum):
            def hello_pylint(self) -> str:
                return self.name

        class Color(EnumSubclass):
            red = 1

        Color.red.hello_pylint()  #@
        """
        )
        assert isinstance(ast_node, nodes.NodeNG)
        inferred = ast_node.inferred()
        self.assertEqual(len(inferred), 1)
        self.assertIsInstance(inferred[0], astroid.Const)
        self.assertEqual(inferred[0].value, "red")

    def test_enum_subclass_different_modules(self) -> None:
        # See Pylint issue #2626
        astroid.extract_node(
            """
        from enum import Enum

        class EnumSubclass(Enum):
            pass
        """,
            "a",
        )
        ast_node = astroid.extract_node(
            """
        from a import EnumSubclass

        class Color(EnumSubclass):
            red = 1

        Color.red.value #@
        """
        )
        assert isinstance(ast_node, nodes.NodeNG)
        inferred = ast_node.inferred()
        self.assertEqual(len(inferred), 1)
        self.assertIsInstance(inferred[0], astroid.Const)
        self.assertEqual(inferred[0].value, 1)

    def test_members_member_ignored(self) -> None:
        ast_node = builder.extract_node(
            """
        from enum import Enum
        class Animal(Enum):
            a = 1
            __members__ = {}
        Animal.__members__ #@
        """
        )

        inferred = next(ast_node.infer())
        self.assertIsInstance(inferred, astroid.Dict)
        self.assertTrue(inferred.locals)

    def test_enum_as_renamed_import(self) -> None:
        """Originally reported in https://github.com/pylint-dev/pylint/issues/5776."""
        ast_node: nodes.Attribute = builder.extract_node(
            """
        from enum import Enum as PyEnum
        class MyEnum(PyEnum):
            ENUM_KEY = "enum_value"
        MyEnum.ENUM_KEY
        """
        )
        inferred = next(ast_node.infer())
        assert isinstance(inferred, bases.Instance)
        assert inferred._proxied.name == "ENUM_KEY"

    def test_class_named_enum(self) -> None:
        """Test that the user-defined class named `Enum` is not inferred as `enum.Enum`"""
        astroid.extract_node(
            """
        class Enum:
            def __init__(self, one, two):
                self.one = one
                self.two = two
            def pear(self):
                ...
        """,
            "module_with_class_named_enum",
        )

        attribute_nodes = astroid.extract_node(
            """
        import module_with_class_named_enum
        module_with_class_named_enum.Enum("apple", "orange") #@
        typo_module_with_class_named_enum.Enum("apple", "orange") #@
        """
        )

        name_nodes = astroid.extract_node(
            """
        from module_with_class_named_enum import Enum
        Enum("apple", "orange") #@
        TypoEnum("apple", "orange") #@
        """
        )

        # Test that both of the successfully inferred `Name` & `Attribute`
        # nodes refer to the user-defined Enum class.
        for inferred in (attribute_nodes[0].inferred()[0], name_nodes[0].inferred()[0]):
            assert isinstance(inferred, astroid.Instance)
            assert inferred.name == "Enum"
            assert inferred.qname() == "module_with_class_named_enum.Enum"
            assert "pear" in inferred.locals

        # Test that an `InferenceError` is raised when an attempt is made to
        # infer a `Name` or `Attribute` node & they cannot be found.
        for node in (attribute_nodes[1], name_nodes[1]):
            with pytest.raises(InferenceError):
                node.inferred()

    def test_enum_members_uppercase_only(self) -> None:
        """Originally reported in https://github.com/pylint-dev/pylint/issues/7402.
        ``nodes.AnnAssign`` nodes with no assigned values do not appear inside ``__members__``.

        Test that only enum members `MARS` and `radius` appear in the `__members__` container while
        the attribute `mass` does not.
        """
        enum_class = astroid.extract_node(
            """
        from enum import Enum
        class Planet(Enum): #@
            MARS = (1, 2)
            radius: int = 1
            mass: int

            def __init__(self, mass, radius):
                self.mass = mass
                self.radius = radius

        Planet.MARS.value
        """
        )
        enum_members = next(enum_class.igetattr("__members__"))
        assert len(enum_members.items) == 2
        mars, radius = enum_members.items
        assert mars[1].name == "MARS"
        assert radius[1].name == "radius"

    def test_local_enum_child_class_inference(self) -> None:
        """Originally reported in https://github.com/pylint-dev/pylint/issues/8897

        Test that a user-defined enum class is inferred when it subclasses
        another user-defined enum class.
        """
        enum_class_node, enum_member_value_node = astroid.extract_node(
            """
        import sys

        from enum import Enum

        if sys.version_info >= (3, 11):
            from enum import StrEnum
        else:
            class StrEnum(str, Enum):
                pass


        class Color(StrEnum): #@
            RED = "red"


        Color.RED.value #@
        """
        )
        assert "RED" in enum_class_node.locals

        enum_members = enum_class_node.locals["__members__"][0].items
        assert len(enum_members) == 1
        _, name = enum_members[0]
        assert name.name == "RED"

        inferred_enum_member_value_node = next(enum_member_value_node.infer())
        assert inferred_enum_member_value_node.value == "red"

    def test_enum_with_ignore(self) -> None:
        """Exclude ``_ignore_`` from the ``__members__`` container
        Originally reported in https://github.com/pylint-dev/pylint/issues/9015
        """

        ast_node: nodes.Attribute = builder.extract_node(
            """
        import enum


        class MyEnum(enum.Enum):
            FOO = enum.auto()
            BAR = enum.auto()
            _ignore_ = ["BAZ"]
            BAZ = 42
        MyEnum.__members__
        """
        )
        inferred = next(ast_node.infer())
        members_names = [const_node.value for const_node, name_obj in inferred.items]
        assert members_names == ["FOO", "BAR", "BAZ"]

    def test_enum_sunder_names(self) -> None:
        """Test that both `_name_` and `_value_` sunder names exist"""

        sunder_name, sunder_value = builder.extract_node(
            """
        import enum


        class MyEnum(enum.Enum):
            APPLE = 42
        MyEnum.APPLE._name_ #@
        MyEnum.APPLE._value_ #@
        """
        )
        inferred_name = next(sunder_name.infer())
        assert inferred_name.value == "APPLE"

        inferred_value = next(sunder_value.infer())
        assert inferred_value.value == 42
