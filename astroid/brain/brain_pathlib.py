# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

from collections.abc import Iterator

from astroid import bases, context, nodes
from astroid.builder import _extract_single_node
from astroid.exceptions import InferenceError, UseInferenceDefault
from astroid.inference_tip import inference_tip
from astroid.manager import AstroidManager

PATH_TEMPLATE = """
from pathlib import Path
Path
"""

# ``pathlib`` was reorganised into a package in Python 3.13, where the classes
# live in ``pathlib._local``, and moved back in Python 3.14.
PUREPATH_QNAMES = frozenset({"pathlib.PurePath", "pathlib._local.PurePath"})


def _parents_attribute(node: nodes.Subscript) -> nodes.Attribute | None:
    """Return the ``parents`` attribute that ``node`` subscripts, if any.

    The attribute can be subscripted directly (``path.parents[0]``) or through
    a name it was assigned to (``parents = path.parents; parents[0]``).
    """
    value = node.value
    if isinstance(value, nodes.Name):
        _, assignments = value.lookup(value.name)
        if len(assignments) != 1:
            return None
        assigned = assignments[0]
        if not (
            isinstance(assigned, nodes.AssignName)
            and isinstance(assigned.parent, nodes.Assign)
            and len(assigned.parent.targets) == 1
        ):
            return None
        value = assigned.parent.value
    if isinstance(value, nodes.Attribute) and value.attrname == "parents":
        return value
    return None


def _looks_like_parents_subscript(node: nodes.Subscript) -> bool:
    attribute = _parents_attribute(node)
    if attribute is None:
        return False

    # Check the object whose ``parents`` are subscripted rather than what the
    # property returns: that is a ``tuple`` on Python 3.13, which any
    # ``parents`` attribute holding a tuple would match, and a private
    # ``pathlib._PathParents`` sequence on the other versions.
    try:
        value = next(attribute.expr.infer())
    except (InferenceError, StopIteration):
        return False
    return (
        isinstance(value, bases.Instance)
        and isinstance(value._proxied, nodes.ClassDef)
        and any(value._proxied.is_subtype_of(qname) for qname in PUREPATH_QNAMES)
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
