# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

from collections.abc import Iterator

from astroid import bases, context, extract_node, inference_tip, nodes
from astroid.exceptions import InferenceError, UseInferenceDefault
from astroid.manager import AstroidManager

PATH = extract_node(
    """from pathlib import Path
Path
"""
)
PATH_CLASSDEF: nodes.ClassDef = next(PATH.infer())


def _looks_like_parents_subscript(node: nodes.Subscript) -> bool:
    if not isinstance(node.value, nodes.Name) and not (
        isinstance(node.value, nodes.Attribute) and node.value.attrname == "parents"
    ):
        return False

    try:
        value = next(node.value.infer())
    except (InferenceError, StopIteration):
        return False
    return (
        isinstance(value, bases.Instance)
        and isinstance(value._proxied, nodes.ClassDef)
        and value.qname() == "pathlib._PathParents"
    )


def infer_parents_subscript(
    subscript_node: nodes.Subscript, ctx: context.InferenceContext | None = None
) -> Iterator[bases.Instance]:
    if isinstance(subscript_node.slice, nodes.Const):
        return iter((PATH_CLASSDEF.instantiate_class(),))

    raise UseInferenceDefault


AstroidManager().register_transform(
    nodes.Subscript,
    inference_tip(infer_parents_subscript),
    _looks_like_parents_subscript,
)
