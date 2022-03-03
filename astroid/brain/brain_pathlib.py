# Copyright (c) 2022 Deepyaman Datta <deepyaman.datta@utexas.edu>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE

from astroid import inference_tip
from astroid.const import PY310_PLUS
from astroid.exceptions import UseInferenceDefault
from astroid.manager import AstroidManager
from astroid.nodes.node_classes import Attribute, Slice, Subscript


def _looks_like_parents_subscript(node):
    return (
        isinstance(node, Subscript)
        and isinstance(node.value, Attribute)
        and node.value.attrname == "parents"
    )


def infer_parents_subscript(subscript_node, context=None):
    if isinstance(subscript_node.slice, Slice):
        raise UseInferenceDefault

    yield from subscript_node.value.expr.infer(context=context)


if PY310_PLUS:
    AstroidManager().register_transform(
        Subscript, inference_tip(infer_parents_subscript), _looks_like_parents_subscript
    )
