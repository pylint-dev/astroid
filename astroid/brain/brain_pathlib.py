# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

from collections.abc import Iterator

from astroid import bases, context, nodes
from astroid.builder import _extract_single_node
from astroid.const import PY313
from astroid.exceptions import InferenceError, UseInferenceDefault
from astroid.inference_tip import inference_tip
from astroid.manager import AstroidManager

PATH_TEMPLATE = """
from pathlib import Path
Path
"""


def _looks_like_parents_value(node: nodes.NodeNG) -> bool:
    """Whether ``node`` refers to a ``.parents`` attribute access.

    A name is accepted when it is assigned such an attribute access, so that
    ``parents = path.parents`` followed by ``parents[0]`` is recognised too.
    """
    if isinstance(node, nodes.Attribute) and node.attrname == "parents":
        return True

    if isinstance(node, nodes.Name):
        _, assignments = node.lookup(node.name)
        return any(
            isinstance(assignment, nodes.AssignName)
            and isinstance(assignment.parent, nodes.Assign)
            and isinstance(assignment.parent.value, nodes.Attribute)
            and assignment.parent.value.attrname == "parents"
            for assignment in assignments
        )

    return False


def _looks_like_parents_subscript(node: nodes.Subscript) -> bool:
    if not _looks_like_parents_value(node.value):
        return False

    try:
        value = next(node.value.infer())
    except (InferenceError, StopIteration):
        return False
    parents = "builtins.tuple" if PY313 else "pathlib._PathParents"
    return (
        isinstance(value, bases.Instance)
        and isinstance(value._proxied, nodes.ClassDef)
        and value.qname() == parents
    )


def infer_parents_subscript(
    subscript_node: nodes.Subscript, ctx: context.InferenceContext | None = None
) -> Iterator[bases.Instance]:
    if isinstance(subscript_node.slice, nodes.Const):
        path_cls = next(_extract_single_node(PATH_TEMPLATE).infer())
        return iter([path_cls.instantiate_class()])

    raise UseInferenceDefault


def register(manager: AstroidManager) -> None:
    manager.register_transform(
        nodes.Subscript,
        inference_tip(infer_parents_subscript),
        _looks_like_parents_subscript,
    )
