# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import unittest

import pytest

try:
    import numpy  # pylint: disable=unused-import

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from astroid import builder


@unittest.skipUnless(HAS_NUMPY, "This test requires the numpy library.")
class BrainNumpyCoreNumericTest(unittest.TestCase):
    """Test the numpy core numeric brain module."""

    numpy_functions = (
        ("zeros_like", "[1, 2]"),
        ("full_like", "[1, 2]", "4"),
        ("ones_like", "[1, 2]"),
        ("ones", "[1, 2]"),
    )

    def _inferred_numpy_func_call(self, func_name, *func_args):
        node = builder.extract_node(
            f"""
        import numpy as np
        func = np.{func_name:s}
        func({','.join(func_args):s})
        """
        )
        return node.infer()

    def test_numpy_function_calls_inferred_as_ndarray(self):
        """Test that calls to numpy functions are inferred as numpy.ndarray."""
        licit_array_types = (".ndarray",)
        for func_ in self.numpy_functions:
            with self.subTest(typ=func_):
                inferred_values = list(self._inferred_numpy_func_call(*func_))
                self.assertTrue(
                    len(inferred_values) == 1,
                    msg=f"Too much inferred value for {func_[0]:s}",
                )
                self.assertTrue(
                    inferred_values[-1].pytype() in licit_array_types,
                    msg="Illicit type for {:s} ({})".format(
                        func_[0], inferred_values[-1].pytype()
                    ),
                )


@pytest.mark.skipif(not HAS_NUMPY, reason="This test requires the numpy library.")
@pytest.mark.parametrize(
    "method, expected_args",
    [
        ("zeros_like", ["a", "dtype", "order", "subok", "shape"]),
        ("full_like", ["a", "fill_value", "dtype", "order", "subok", "shape"]),
        ("ones_like", ["a", "dtype", "order", "subok", "shape"]),
        ("ones", ["shape", "dtype", "order"]),
    ],
)
def test_function_parameters(method: str, expected_args: list[str]) -> None:
    instance = builder.extract_node(
        f"""
    import numpy
    numpy.{method} #@
    """
    )
    actual_args = instance.inferred()[0].args.args
    assert [arg.name for arg in actual_args] == expected_args
