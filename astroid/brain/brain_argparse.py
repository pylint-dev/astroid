# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

from typing import TYPE_CHECKING

from astroid import arguments, nodes
from astroid.exceptions import UseInferenceDefault
from astroid.inference_tip import inference_tip
from astroid.manager import AstroidManager

if TYPE_CHECKING:
    from astroid.context import InferenceContext


def infer_namespace(node, context: InferenceContext | None = None):
    callsite = arguments.CallSite.from_call(node, context=context)
    if not callsite.keyword_arguments:
        # Cannot make sense of it.
        raise UseInferenceDefault()

    class_node = nodes.ClassDef(
        "Namespace",
        lineno=node.lineno,
        col_offset=node.col_offset,
        parent=AstroidManager().adhoc_module,  # this class is not real
        end_lineno=node.end_lineno,
        end_col_offset=node.end_col_offset,
    )
    for attr in set(callsite.keyword_arguments):
        fake_node = nodes.EmptyNode()
        fake_node.parent = class_node
        fake_node.attrname = attr
        class_node.instance_attrs[attr] = [fake_node]
    return iter((class_node.instantiate_class(),))


def _looks_like_namespace(node) -> bool:
    func = node.func
    if isinstance(func, nodes.Attribute):
        return (
            func.attrname == "Namespace"
            and isinstance(func.expr, nodes.Name)
            and func.expr.name == "argparse"
        )
    return False


def register(manager: AstroidManager) -> None:
    manager.register_transform(
        nodes.Call, inference_tip(infer_namespace), _looks_like_namespace
    )
