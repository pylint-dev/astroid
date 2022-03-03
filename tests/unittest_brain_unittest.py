# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/graphs/contributors
import unittest

from astroid import builder
from astroid.test_utils import require_version


class UnittestTest(unittest.TestCase):
    """
    A class that tests the brain_unittest module
    """

    @require_version(minver="3.8.0")
    def test_isolatedasynciotestcase(self):
        """
        Tests that the IsolatedAsyncioTestCase class is statically imported
        thanks to the brain_unittest module.
        """
        node = builder.extract_node(
            """
        from unittest import IsolatedAsyncioTestCase

        class TestClass(IsolatedAsyncioTestCase):
            pass
        """
        )
        assert [n.qname() for n in node.ancestors()] == [
            "unittest.async_case.IsolatedAsyncioTestCase",
            "unittest.case.TestCase",
            "builtins.object",
        ]
