# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import unittest
import warnings

import astroid
from astroid import builder

try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        import nose  # pylint: disable=unused-import
    HAS_NOSE = True
except ImportError:
    HAS_NOSE = False


@unittest.skipUnless(HAS_NOSE, "This test requires nose library.")
class NoseBrainTest(unittest.TestCase):
    def test_nose_tools(self):
        methods = builder.extract_node(
            """
        from nose.tools import assert_equal
        from nose.tools import assert_equals
        from nose.tools import assert_true
        assert_equal = assert_equal #@
        assert_true = assert_true #@
        assert_equals = assert_equals #@
        """
        )
        assert isinstance(methods, list)
        assert_equal = next(methods[0].value.infer())
        assert_true = next(methods[1].value.infer())
        assert_equals = next(methods[2].value.infer())

        self.assertIsInstance(assert_equal, astroid.BoundMethod)
        self.assertIsInstance(assert_true, astroid.BoundMethod)
        self.assertIsInstance(assert_equals, astroid.BoundMethod)
        self.assertEqual(assert_equal.qname(), "unittest.case.TestCase.assertEqual")
        self.assertEqual(assert_true.qname(), "unittest.case.TestCase.assertTrue")
        self.assertEqual(assert_equals.qname(), "unittest.case.TestCase.assertEqual")
