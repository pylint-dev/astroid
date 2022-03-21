# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

import sys
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from astroid import nodes
    from astroid.context import InferenceContext

if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict


class InferenceErrorInfo(TypedDict):
    """Store additional Inference error information
    raised with StopIteration exception.
    """

    node: "nodes.NodeNG"
    context: "InferenceContext | None"


InferFn = Callable[..., Any]
