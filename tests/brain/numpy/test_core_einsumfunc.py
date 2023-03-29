# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import pytest

from astroid import builder, nodes

try:
    import numpy  # pylint: disable=unused-import

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


def _inferred_numpy_func_call(func_name: str, *func_args: str) -> nodes.FunctionDef:
    node = builder.extract_node(
        f"""
    import numpy as np
    func = np.{func_name:s}
    func({','.join(func_args):s})
    """
    )
    return node.infer()


@pytest.mark.skipif(not HAS_NUMPY, reason="This test requires the numpy library.")
def test_numpy_function_calls_inferred_as_ndarray() -> None:
    """Test that calls to numpy functions are inferred as numpy.ndarray."""
    method = "einsum"
    inferred_values = list(
        _inferred_numpy_func_call(method, "ii, np.arange(25).reshape(5, 5)")
    )

    assert len(inferred_values) == 1, f"Too much inferred value for {method:s}"
    assert (
        inferred_values[-1].pytype() == ".ndarray"
    ), f"Illicit type for {method:s} ({inferred_values[-1].pytype()})"


@pytest.mark.skipif(not HAS_NUMPY, reason="This test requires the numpy library.")
def test_function_parameters() -> None:
    instance = builder.extract_node(
        """
    import numpy
    numpy.einsum #@
    """
    )
    actual_args = instance.inferred()[0].args

    assert actual_args.vararg == "operands"
    assert [arg.name for arg in actual_args.kwonlyargs] == ["out", "optimize"]
    assert actual_args.kwarg == "kwargs"
