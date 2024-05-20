# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import unittest

from astroid import builder


class UnittestTest(unittest.TestCase):
    """A class that tests the brain_unittest module."""

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
