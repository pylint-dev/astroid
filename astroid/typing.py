# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

import sys
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterator, List, Set

if TYPE_CHECKING:
    from astroid import nodes, transforms
    from astroid.context import InferenceContext

if sys.version_info >= (3, 8):
    from typing import Protocol, TypedDict
else:
    from typing_extensions import Protocol, TypedDict


class InferenceErrorInfo(TypedDict):
    """Store additional Inference error information
    raised with StopIteration exception.
    """

    node: "nodes.NodeNG"
    context: "InferenceContext | None"


InferFn = Callable[..., Any]


class AstroidManagerBrain(TypedDict):
    """Dictionary to store relevant information for a AstroidManager class."""

    astroid_cache: Dict
    _mod_file_cache: Dict
    _failed_import_hooks: List
    always_load_extensions: bool
    optimize_ast: bool
    extension_package_whitelist: Set
    _transform: "transforms.TransformVisitor"


class InferMethod(Protocol):
    def __call__(  # pylint: disable=no-self-argument
        self_, self: "nodes.NodeNG", context: "InferenceContext | None" = None
    ) -> Iterator["nodes.NodeNG"]:
        ...
