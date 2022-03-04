# Copyright (c) 2022 Deepyaman Datta <deepyaman.datta@utexas.edu>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE

from typing import Iterator, Optional

from astroid import bases, context, inference_tip
from astroid.const import PY310_PLUS
from astroid.exceptions import UseInferenceDefault
from astroid.manager import AstroidManager
from astroid.nodes.node_classes import Attribute, Slice, Subscript
from astroid.nodes.node_ng import NodeNG


def _looks_like_parents_subscript(node: NodeNG) -> bool:
    return (
        isinstance(node, Subscript)
        and isinstance(node.value, Attribute)
        and node.value.attrname == "parents"
    )


def infer_parents_subscript(
    subscript_node: Subscript, ctx: Optional[context.InferenceContext] = None
) -> Iterator[bases.Instance]:
    if isinstance(subscript_node.slice, Slice):
        raise UseInferenceDefault

    yield from subscript_node.value.expr.infer(context=ctx)


if PY310_PLUS:
    AstroidManager().register_transform(
        Subscript, inference_tip(infer_parents_subscript), _looks_like_parents_subscript
    )
