# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import datetime
import types
import unittest

import pytest

import astroid
from astroid import bases, builder, nodes
from astroid.exceptions import InferenceError
from astroid.manager import AstroidManager


class EnumBrainTest(unittest.TestCase):
    def test_enum_predicate_does_not_raise_for_extension_class(self) -> None:
        """Classes introspected from extensions can have an unresolvable base.

        Regression test for pylint-dev/pylint#11179.
        """
        module_name = "extension_module"
        module = types.ModuleType(module_name)
        module.datetime = datetime
        extension_class = type("ExtensionClass", (datetime.datetime,), {})
        extension_class.__module__ = module_name
        module.ExtensionClass = extension_class

        builder.AstroidBuilder(AstroidManager()).module_build(module, module_name)

    def test_simple_enum(self) -> None:
        module = builder.parse("""
        import enum

        class MyEnum(enum.Enum):
            one = "one"
            two = "two"

            def mymethod(self, x):
                return 5

        """)

        enumeration = next(module["MyEnum"].infer())
        one = enumeration["one"]
        self.assertEqual(one.pytype(), ".MyEnum.one")

        for propname in ("name", "value"):
            prop = next(iter(one.getattr(propname)))
            self.assertIn("builtins.property", prop.decoratornames())

        meth = one.getattr("mymethod")[0]
        self.assertIsInstance(meth, nodes.FunctionDef)

    def test_infer_enum_value_as_the_right_type(self) -> None:
        string_value, int_value = builder.extract_node("""
        from enum import Enum
        class A(Enum):
            a = 'a'
            b = 1
        A.a.value #@
        A.b.value #@
        """)
        inferred_string = string_value.inferred()
        assert any(
            isinstance(elem, nodes.Const) and elem.value == "a"
            for elem in inferred_string
        )

        inferred_int = int_value.inferred()
        assert any(
            isinstance(elem, nodes.Const) and elem.value == 1 for elem in inferred_int
        )

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
        ast_node = astroid.extract_node("""
        from a import EnumSubclass

        class Color(EnumSubclass):
            red = 1

        Color.red.value #@
        """)
        assert isinstance(ast_node, nodes.NodeNG)
        inferred = ast_node.inferred()
        self.assertEqual(len(inferred), 1)
        self.assertIsInstance(inferred[0], nodes.Const)
        self.assertEqual(inferred[0].value, 1)

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

        attribute_nodes = astroid.extract_node("""
        import module_with_class_named_enum
        module_with_class_named_enum.Enum("apple", "orange") #@
        typo_module_with_class_named_enum.Enum("apple", "orange") #@
        """)

        name_nodes = astroid.extract_node("""
        from module_with_class_named_enum import Enum
        Enum("apple", "orange") #@
        TypoEnum("apple", "orange") #@
        """)

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

    def test_enum_with_ignore(self) -> None:
        """Exclude ``_ignore_`` from the ``__members__`` container
        Originally reported in https://github.com/pylint-dev/pylint/issues/9015
        """

        ast_node: nodes.Attribute = builder.extract_node("""
        import enum


        class MyEnum(enum.Enum):
            FOO = enum.auto()
            BAR = enum.auto()
            _ignore_ = ["BAZ"]
            BAZ = 42
        MyEnum.__members__
        """)
        inferred = next(ast_node.infer())
        members_names = [const_node.value for const_node, name_obj in inferred.items]
        assert members_names == ["FOO", "BAR", "BAZ"]

    def test_enum_oversized_integer_member(self) -> None:
        """An int member past ``sys.get_int_max_str_digits()`` is still mocked.

        A hexadecimal literal is accepted by the tokenizer, but rendering its
        value back in decimal used to make the enum transform raise ``ValueError``.
        """
        oversized = "0x" + "f" * 4000
        big_value, small_value = builder.extract_node(f"""
        import enum

        class Flags(enum.IntFlag):
            A = {oversized}
            B = 2

        Flags.A.value  #@
        Flags.B.value  #@
        """)
        inferred = next(big_value.infer())
        assert isinstance(inferred, nodes.Const)
        assert inferred.value == int(oversized, 16)
        inferred = next(small_value.infer())
        assert isinstance(inferred, nodes.Const)
        assert inferred.value == 2

    def test_dataclass_enum_exposes_members(self) -> None:
        """Regression test for https://github.com/pylint-dev/astroid/issues/2317.

        A class decorated with ``@dataclass`` that also inherits from ``Enum``
        must still expose ``__members__`` (the dataclass transform should not
        strip the enum metaclass attributes).
        """
        ast_node = builder.extract_node("""
        from dataclasses import dataclass
        from enum import Enum


        @dataclass
        class Something(str, Enum):
            A = "a"
            B = "b"

        Something.__members__  #@
        """)
        inferred = next(ast_node.infer())
        assert isinstance(inferred, nodes.Dict)
        member_names = [key.value for key, _ in inferred.items]
        assert member_names == ["A", "B"]

    def test_enum_members_from_imports_in_class_body(self) -> None:
        """Names bound by an import in the class body are enum members.

        Regression test for https://github.com/pylint-dev/pylint/issues/10951
        """
        member, value, alias_value, module_member, members = builder.extract_node("""
        import enum

        class LogLevel(enum.IntEnum):
            from logging import (
                CRITICAL as CRITICAL_LEVEL,
                DEBUG,
            )

        class Modules(enum.Enum):
            import os.path
            import json as JSON

        LogLevel.DEBUG #@
        LogLevel.DEBUG.value #@
        LogLevel.CRITICAL_LEVEL.value #@
        Modules.JSON #@
        LogLevel.__members__ #@
        """)
        inferred_member = next(member.infer())
        assert isinstance(inferred_member, bases.Instance)
        assert inferred_member.pytype() == ".LogLevel.DEBUG"

        inferred_value = next(value.infer())
        assert isinstance(inferred_value, nodes.Const)
        assert inferred_value.value == 10

        inferred_alias_value = next(alias_value.infer())
        assert isinstance(inferred_alias_value, nodes.Const)
        assert inferred_alias_value.value == 50

        inferred_module_member = next(module_member.infer())
        assert isinstance(inferred_module_member, bases.Instance)
        assert inferred_module_member.pytype() == ".Modules.JSON"
        assert isinstance(next(inferred_module_member.igetattr("value")), nodes.Module)

        inferred_members = next(members.infer())
        assert [key.value for key, _ in inferred_members.items] == [
            "CRITICAL_LEVEL",
            "DEBUG",
        ]

    def test_enum_descriptor_imported_in_class_body_is_not_a_member(self) -> None:
        """A descriptor, such as a function or a class defining ``__get__``,
        is not a member, even when it is bound by an import.
        """
        function, call, members = builder.extract_node("""
        import enum

        class Color(enum.Enum):
            from os.path import join
            from functools import cached_property
            from collections import OrderedDict
            RED = 1

        Color.join #@
        Color.join("a", "b") #@
        Color.__members__ #@
        """)
        inferred_function = next(function.infer())
        assert isinstance(inferred_function, bases.UnboundMethod)
        assert inferred_function.name == "join"

        # Calling the member mock used to raise ``InferenceError``. What the
        # call infers to depends on the ``os.path.join`` of the Python version.
        assert list(call.infer())

        inferred_members = next(members.infer())
        assert {key.value for key, _ in inferred_members.items} == {
            "OrderedDict",
            "RED",
        }
