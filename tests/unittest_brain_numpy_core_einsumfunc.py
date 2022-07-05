# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import pytest

try:
    import numpy  # pylint: disable=unused-import

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from astroid import builder


def _inferred_numpy_func_call(func_name, *func_args):
    node = builder.extract_node(
        f"""
    import numpy as np
    func = np.{func_name:s}
    func({','.join(func_args):s})
    """
    )
    return node.infer()


@pytest.mark.skipif(not HAS_NUMPY, reason="This test requires the numpy library.")
@pytest.mark.parametrize(
    "method, args",
    [
        ("einsum", "ii, np.arange(25).reshape(5, 5)"),
    ],
)
def test_numpy_function_calls_inferred_as_ndarray(method, args):
    """
    Test that calls to numpy functions are inferred as numpy.ndarray
    """
    licit_array_types = (".ndarray",)
    inferred_values = list(_inferred_numpy_func_call(method, args))
    assert len(inferred_values) == 1, f"Too much inferred value for {method:s}"
    assert (
        inferred_values[-1].pytype() in licit_array_types
    ), f"Illicit type for {method:s} ({inferred_values[-1].pytype()})"


@pytest.mark.skipif(not HAS_NUMPY, reason="This test requires the numpy library.")
@pytest.mark.parametrize(
    "method,   expected_vararg, expected_kwonlyargs, expected_kwarg",
    [
        ("einsum", "operands", ["out", "optimize"], "kwargs"),
    ],
)
def test_function_parameters(
    method: str,
    expected_vararg: str,
    expected_kwonlyargs: list[str],
    expected_kwarg: str,
) -> None:
    instance = builder.extract_node(
        f"""
    import numpy
    numpy.{method} #@
    """
    )
    actual_args = instance.inferred()[0].args

    assert actual_args.vararg == expected_vararg
    assert [arg.name for arg in actual_args.kwonlyargs] == expected_kwonlyargs
    assert actual_args.kwarg == expected_kwarg
