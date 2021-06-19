# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/LICENSE

"""Transform utilities (filters and decorator)"""

import itertools

import wrapt

# pylint: disable=dangerous-default-value
from astroid.exceptions import InferenceOverwriteError


@wrapt.decorator
def _inference_tip_cached(func, instance, args, kwargs, _cache={}):  # noqa:B006
    """Cache decorator used for inference tips"""
    node = args[0]
    try:
        return iter(_cache[func, node])
    except KeyError:
        result = func(*args, **kwargs)
        # Need to keep an iterator around
        original, copy = itertools.tee(result)
        _cache[func, node] = list(copy)
        return original


# pylint: enable=dangerous-default-value


def inference_tip(infer_function, raise_on_overwrite=False):
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

    def transform(node, infer_function=infer_function):
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
        node._explicit_inference = _inference_tip_cached(infer_function)
        return node

    return transform
