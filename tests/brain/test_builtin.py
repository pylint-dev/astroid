# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Unit Tests for the builtins brain module."""

import unittest

import pytest

from astroid import nodes, objects, util
from astroid.builder import _extract_single_node, extract_node


class BuiltinsTest(unittest.TestCase):
    def test_infer_property(self):
        class_with_property = _extract_single_node(
            """
        class Something:
            def getter():
                return 5
            asd = property(getter) #@
        """
        )
        inferred_property = next(iter(class_with_property.value.infer()))
        self.assertTrue(isinstance(inferred_property, objects.Property))
        class_parent = inferred_property.parent.parent.parent
        self.assertIsInstance(class_parent, nodes.ClassDef)
        self.assertFalse(
            any(
                isinstance(getter, objects.Property)
                for getter in class_parent.locals["getter"]
            )
        )
        self.assertTrue(hasattr(inferred_property, "args"))


class TestStringNodes:
    @pytest.mark.parametrize(
        "format_string",
        [
            pytest.param(
                """"My name is {}, I'm {}".format("Daniel", 12)""", id="empty-indexes"
            ),
            pytest.param(
                """"My name is {0}, I'm {1}".format("Daniel", 12)""",
                id="numbered-indexes",
            ),
            pytest.param(
                """"My name is {fname}, I'm {age}".format(fname = "Daniel", age = 12)""",
                id="named-indexes",
            ),
            pytest.param(
                """
        name = "Daniel"
        age = 12
        "My name is {0}, I'm {1}".format(name, age)
        """,
                id="numbered-indexes-from-positional",
            ),
            pytest.param(
                """
        name = "Daniel"
        age = 12
        "My name is {fname}, I'm {age}".format(fname = name, age = age)
        """,
                id="named-indexes-from-keyword",
            ),
            pytest.param(
                """
        name = "Daniel"
        age = 12
        "My name is {0}, I'm {age}".format(name, age = age)
        """,
                id="mixed-indexes-from-mixed",
            ),
            pytest.param(
                """
        string = "My name is {}, I'm {}"
        string.format("Daniel", 12)
        """,
                id="empty-indexes-on-variable",
            ),
        ],
    )
    def test_string_format(self, format_string: str) -> None:
        node: nodes.Call = _extract_single_node(format_string)
        inferred = next(node.infer())
        assert isinstance(inferred, nodes.Const)
        assert inferred.value == "My name is Daniel, I'm 12"

    @pytest.mark.parametrize(
        "format_string",
        [
            """
            from missing import Unknown
            name = Unknown
            age = 12
            "My name is {fname}, I'm {age}".format(fname = name, age = age)
            """,
            """
            from missing import Unknown
            age = 12
            "My name is {fname}, I'm {age}".format(fname = Unknown, age = age)
            """,
            """
            from missing import Unknown
            "My name is {}, I'm {}".format(Unknown, 12)
            """,
            """"I am {}".format()""",
            """
            "My name is {fname}, I'm {age}".format(fsname = "Daniel", age = 12)
            """,
            """
            "My unicode character is {:c}".format(None)
            """,
            """
            "My hex format is {:4x}".format('1')
            """,
            """
            daniel_age = 12
            "My name is {0.name}".format(daniel_age)
            """,
        ],
    )
    def test_string_format_uninferable(self, format_string: str) -> None:
        node: nodes.Call = _extract_single_node(format_string)
        inferred = next(node.infer())
        assert inferred is util.Uninferable

    def test_string_format_with_specs(self) -> None:
        node: nodes.Call = _extract_single_node(
            """"My name is {}, I'm {:.2f}".format("Daniel", 12)"""
        )
        inferred = next(node.infer())
        assert isinstance(inferred, nodes.Const)
        assert inferred.value == "My name is Daniel, I'm 12.00"

    def test_string_format_in_dataclass_pylint8109(self) -> None:
        """https://github.com/pylint-dev/pylint/issues/8109"""
        function_def = extract_node(
            """
from dataclasses import dataclass

@dataclass
class Number:
    amount: int | float
    round: int = 2

    def __str__(self): #@
        number_format = "{:,.%sf}" % self.round
        return number_format.format(self.amount).rstrip("0").rstrip(".")
"""
        )
        inferit = function_def.infer_call_result(function_def, context=None)
        assert [a.name for a in inferit] == [util.Uninferable]
