# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Tests for brain statistics module."""

from __future__ import annotations

import unittest

from astroid import extract_node
from astroid.util import Uninferable


class StatisticsBrainTest(unittest.TestCase):
    """Test the brain statistics module functionality."""

    def test_statistics_quantiles_inference(self) -> None:
        """Test that statistics.quantiles() returns Uninferable instead of empty list."""
        node = extract_node(
            """
        import statistics
        statistics.quantiles(list(range(100)), n=4)  #@
        """
        )
        inferred = list(node.infer())
        self.assertEqual(len(inferred), 1)
        self.assertIs(inferred[0], Uninferable)

    def test_statistics_quantiles_different_args(self) -> None:
        """Test statistics.quantiles with different arguments."""
        node = extract_node(
            """
        import statistics
        statistics.quantiles([1, 2, 3, 4, 5], n=10, method='inclusive')  #@
        """
        )
        inferred = list(node.infer())
        self.assertEqual(len(inferred), 1)
        self.assertIs(inferred[0], Uninferable)

    def test_statistics_quantiles_assignment_unpacking(self) -> None:
        """Test the specific case that was causing false positives."""
        node = extract_node(
            """
        import statistics
        q1, q2, q3 = statistics.quantiles(list(range(100)), n=4)  #@
        """
        )
        call_node = node.value
        inferred = list(call_node.infer())
        self.assertEqual(len(inferred), 1)
        self.assertIs(inferred[0], Uninferable)

    def test_other_statistics_functions_not_affected(self) -> None:
        """Test that other statistics functions are not affected by our brain module."""
        node = extract_node(
            """
        import statistics
        statistics.mean([1, 2, 3, 4, 5])  #@
        """
        )
        inferred = list(node.infer())
        self.assertNotEqual(len(inferred), 0)


if __name__ == "__main__":
    unittest.main()
