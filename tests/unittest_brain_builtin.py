# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/graphs/contributors
"""Unit Tests for the builtins brain module."""

import unittest

from astroid import extract_node, objects


class BuiltinsTest(unittest.TestCase):
    def test_infer_property(self):
        class_with_property = extract_node(
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
