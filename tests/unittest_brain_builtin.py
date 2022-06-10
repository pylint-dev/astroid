# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

"""Unit Tests for the builtins brain module."""

import unittest

import pytest

from astroid import nodes, objects, util
from astroid.builder import _extract_single_node


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
        inferred_property = list(class_with_property.value.infer())[0]
        self.assertTrue(isinstance(inferred_property, objects.Property))
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
