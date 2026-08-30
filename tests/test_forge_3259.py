"""Regression test for IndexError when inferring function arguments.

See: https://github.com/pylint-dev/astroid/issues/3259
"""
from __future__ import annotations

import pytest

from astroid import extract_node
from astroid.exceptions import NoDefault


def test_default_value_no_index_error_with_duplicate_vararg_kwonlyarg_name() -> None:
    """A keyword-only argument sharing the vararg name must not corrupt
    the default-value index calculation, causing an IndexError."""
    code = "def f(x, *y, y: tuple[x]):\n    pass"
    node = extract_node(code)
    args = node.args
    # 'x' has no default value; default_value should raise NoDefault,
    # not IndexError.
    with pytest.raises(NoDefault):
        args.default_value("x")


def test_infer_annotation_no_crash() -> None:
    """Inferring the annotation ``tuple[x]`` should not raise."""
    code = "def f(x, *y, y: tuple[x]):\n    pass"
    node = extract_node(code)
    # The annotation of the keyword-only argument 'y' is tuple[x].
    kwonly_arg = node.args.kwonlyargs[0]
    annotation = node.args.kwonlyargs_annotations[0]
    # This used to raise IndexError -> AstroidError.
    results = list(annotation.infer())
    assert results, "Expected at least one inference result for the annotation"