# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Tests for the numpy version detection shared by the numpy brains.

These tests drive the compatibility layer directly, so they run whatever
version of numpy is installed, and even when numpy is not installed at all.
"""

from __future__ import annotations

import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from unittest import mock

from astroid import nodes
from astroid.brain import brain_numpy_utils
from astroid.brain.brain_numpy_core_multiarray import numpy_core_multiarray_transform
from astroid.brain.brain_numpy_core_numerictypes import (
    numpy_core_numerictypes_transform,
)
from astroid.brain.brain_numpy_core_umath import numpy_core_umath_transform
from astroid.brain.brain_numpy_ndarray import infer_numpy_ndarray

NUMPY_1 = (1, 26, 4)
NUMPY_2 = (2, 2, 6)


@contextmanager
def installed_numpy(version: tuple[int, ...] | None) -> Iterator[None]:
    """Pretend that the given version of numpy is the installed one."""
    with mock.patch.object(brain_numpy_utils, "numpy_version", lambda: version):
        yield


class NumpyVersionTest(unittest.TestCase):
    """Test the parsing of the version reported by the numpy distribution."""

    def test_release_version(self):
        self.assertEqual(brain_numpy_utils._parse_version("2.2.6"), (2, 2, 6))
        self.assertEqual(brain_numpy_utils._parse_version("1.26.4"), (1, 26, 4))

    def test_pre_release_and_development_versions(self):
        """Everything after the first non numeric component is dropped."""
        self.assertEqual(brain_numpy_utils._parse_version("2.0.0rc1"), (2, 0, 0))
        self.assertEqual(
            brain_numpy_utils._parse_version("2.4.0.dev0+g1234"), (2, 4, 0)
        )

    def test_unparsable_version(self):
        self.assertIsNone(brain_numpy_utils._parse_version("banana"))
        self.assertIsNone(brain_numpy_utils._parse_version(""))

    def test_versions_are_compared_as_numbers(self):
        """A string comparison would consider 1.9 more recent than 1.20."""
        with installed_numpy((1, 9, 0)):
            self.assertFalse(brain_numpy_utils.numpy_supports_type_hints())
        with installed_numpy((1, 20, 0)):
            self.assertTrue(brain_numpy_utils.numpy_supports_type_hints())

    def test_numpy_2_or_later(self):
        for version, expected in (
            ((1, 26, 4), False),
            ((2, 0, 0), True),
            ((2, 2, 6), True),
            ((3, 0, 0), True),
        ):
            with self.subTest(version=version), installed_numpy(version):
                self.assertIs(brain_numpy_utils.numpy_2_or_later(), expected)

    def test_unknown_version_assumes_the_latest_api(self):
        """When numpy is not installed the most recent API is described."""
        with installed_numpy(None):
            self.assertTrue(brain_numpy_utils.numpy_2_or_later())
            self.assertTrue(brain_numpy_utils.numpy_supports_type_hints())


class NumpyBrainCompatibilityTest(unittest.TestCase):
    """Test that the numpy brains describe the installed version of numpy."""

    def test_numerictypes_aliases_removed_in_numpy_2(self):
        with installed_numpy(NUMPY_1):
            module = numpy_core_numerictypes_transform()
        self.assertIn("float_", module.locals)
        self.assertNotIn("ulong", module.locals)

        with installed_numpy(NUMPY_2):
            module = numpy_core_numerictypes_transform()
        self.assertNotIn("float_", module.locals)
        self.assertIn("ulong", module.locals)

    def test_numerictypes_subscript_support(self):
        with installed_numpy((1, 19, 5)):
            module = numpy_core_numerictypes_transform()
        self.assertNotIn("__class_getitem__", module.locals["generic"][0].locals)

        with installed_numpy(NUMPY_2):
            module = numpy_core_numerictypes_transform()
        self.assertIn("__class_getitem__", module.locals["generic"][0].locals)

    def test_umath_ufuncs_added_in_numpy_2(self):
        with installed_numpy(NUMPY_1):
            self.assertNotIn("bitwise_count", numpy_core_umath_transform().locals)

        with installed_numpy(NUMPY_2):
            self.assertIn("bitwise_count", numpy_core_umath_transform().locals)

    def test_multiarray_ufuncs_added_in_numpy_2(self):
        with installed_numpy(NUMPY_1):
            self.assertNotIn("vecdot", numpy_core_multiarray_transform().locals)

        with installed_numpy(NUMPY_2):
            self.assertIn("vecdot", numpy_core_multiarray_transform().locals)

    def test_ndarray_members_added_in_numpy_2(self):
        with installed_numpy(NUMPY_1):
            ndarray = next(infer_numpy_ndarray(None))
        self.assertIsInstance(ndarray, nodes.ClassDef)
        self.assertNotIn("mT", ndarray.locals)
        self.assertNotIn("to_device", ndarray.locals)

        with installed_numpy(NUMPY_2):
            ndarray = next(infer_numpy_ndarray(None))
        self.assertIn("mT", ndarray.locals)
        self.assertIn("to_device", ndarray.locals)

    def test_ndarray_subscript_support(self):
        with installed_numpy((1, 19, 5)):
            ndarray = next(infer_numpy_ndarray(None))
        self.assertNotIn("__class_getitem__", ndarray.locals)

        with installed_numpy(NUMPY_2):
            ndarray = next(infer_numpy_ndarray(None))
        self.assertIn("__class_getitem__", ndarray.locals)


if __name__ == "__main__":
    unittest.main()
