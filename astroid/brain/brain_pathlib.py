# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

from typing import Iterator, Optional

from astroid import bases, context, inference_tip, nodes
from astroid.const import PY310_PLUS
from astroid.exceptions import InferenceError, UseInferenceDefault
from astroid.manager import AstroidManager


def _looks_like_parents_subscript(node: nodes.Subscript) -> bool:
    return isinstance(node.value, nodes.Attribute) and node.value.attrname == "parents"


def infer_parents_subscript(
    subscript_node: nodes.Subscript, ctx: Optional[context.InferenceContext] = None
) -> Iterator[bases.Instance]:
    try:
        value = next(subscript_node.value.infer())
    except (InferenceError, StopIteration) as exc:
        raise UseInferenceDefault from exc

    if value.qname() != "pathlib._PathParents":
        raise UseInferenceDefault

    if isinstance(subscript_node.slice, nodes.Slice):
        raise UseInferenceDefault

    yield from subscript_node.value.expr.infer(context=ctx)


AstroidManager().register_transform(
    nodes.Subscript,
    inference_tip(infer_parents_subscript),
    _looks_like_parents_subscript,
)
