# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Transform utilities (filters and decorator)."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

from astroid.context import InferenceContext
from astroid.exceptions import InferenceOverwriteError, UseInferenceDefault
from astroid.nodes import NodeNG
from astroid.typing import InferenceResult, InferFn, InferFnExplicit, InferFnTransform

_cache: dict[
    tuple[InferFn, NodeNG, InferenceContext | None], list[InferenceResult]
] = {}

_CURRENTLY_INFERRING: set[tuple[InferFn, NodeNG]] = set()


def clear_inference_tip_cache() -> None:
    """Clear the inference tips cache."""
    _cache.clear()


def _inference_tip_cached(func: InferFn) -> InferFnExplicit:
    """Cache decorator used for inference tips."""

    def inner(
        node: NodeNG,
        context: InferenceContext | None,
        **kwargs: Any,
    ) -> Iterator[InferenceResult] | list[InferenceResult]:
        partial_cache_key = (func, node)
        if partial_cache_key in _CURRENTLY_INFERRING:
            # If through recursion we end up trying to infer the same
            # func + node we raise here.
            raise UseInferenceDefault
        try:
            return _cache[func, node, context]
        except KeyError:
            # Recursion guard with a partial cache key.
            # Using the full key causes a recursion error on PyPy.
            # It's a pragmatic compromise to avoid so much recursive inference
            # with slightly different contexts while still passing the simple
            # test cases included with this commit.
            _CURRENTLY_INFERRING.add(partial_cache_key)
            result = _cache[func, node, context] = list(func(node, context, **kwargs))
            # Remove recursion guard.
            _CURRENTLY_INFERRING.remove(partial_cache_key)

        return iter(result)

    return inner


def inference_tip(
    infer_function: InferFn, raise_on_overwrite: bool = False
) -> InferFnTransform:
    """Given an instance specific inference function, return a function to be
    given to AstroidManager().register_transform to set this inference function.

    :param bool raise_on_overwrite: Raise an `InferenceOverwriteError`
        if the inference tip will overwrite another. Used for debugging

    Typical usage

    .. sourcecode:: python

       AstroidManager().register_transform(Call, inference_tip(infer_named_tuple),
                                  predicate)

    .. Note::

        Using an inference tip will override
        any previously set inference tip for the given
        node. Use a predicate in the transform to prevent
        excess overwrites.
    """

    def transform(node: NodeNG, infer_function: InferFn = infer_function) -> NodeNG:
        if (
            raise_on_overwrite
            and node._explicit_inference is not None
            and node._explicit_inference is not infer_function
        ):
            raise InferenceOverwriteError(
                "Inference already set to {existing_inference}. "
                "Trying to overwrite with {new_inference} for {node}".format(
                    existing_inference=infer_function,
                    new_inference=node._explicit_inference,
                    node=node,
                )
            )
        node._explicit_inference = _inference_tip_cached(infer_function)
        return node

    return transform
