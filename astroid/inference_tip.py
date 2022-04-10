# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

"""Transform utilities (filters and decorator)"""

import typing

import wrapt

from astroid import bases, util
from astroid.cache import LRUCache
from astroid.exceptions import InferenceOverwriteError, UseInferenceDefault
from astroid.nodes import NodeNG
from astroid.typing import InferFn

InferOptions = typing.Union[
    NodeNG, bases.Instance, bases.UnboundMethod, typing.Type[util.Uninferable]
]


_INFERENCE_TIP_CACHE: LRUCache = LRUCache()


@wrapt.decorator
def _cached_generator(
    func: InferFn,
    instance: typing.Any,
    args: typing.Tuple[typing.Any, ...],
    kwargs: typing.Dict[str, typing.Any],
) -> typing.Any:
    key = func, args[0]

    if key in _INFERENCE_TIP_CACHE:
        result = _INFERENCE_TIP_CACHE[key]

        if result is None:
            raise UseInferenceDefault()
    else:
        _INFERENCE_TIP_CACHE[key] = None
        result = _INFERENCE_TIP_CACHE[key] = list(func(*args, **kwargs))

    return iter(result)


def inference_tip(infer_function: InferFn, raise_on_overwrite: bool = False) -> InferFn:
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

        # pylint: disable=no-value-for-parameter
        node._explicit_inference = _cached_generator(infer_function)
        return node

    return transform
