# -*- coding: utf-8 -*-
import sys

from astroid import (
    MANAGER,
    extract_node,
    inference_tip,
    nodes,
)


def _looks_like_type_subscript(node):
    """Try to figure out if a Subscript node *might* be a typing-related subscript"""
    if isinstance(node, nodes.Name):
        return node.name == "type"
    if isinstance(node, nodes.Subscript):
        if isinstance(node.value, Name) and node.value.name == "type":
            return True
    return False


def infer_type_sub(node, context=None):
    """Infer a typing.X[...] subscript"""
    sub_node = node.parent
    if not isinstance(sub_node, nodes.Subscript):
        raise UseInferenceDefault
    class_src = """
    class type:
        def __class_getitem__(cls, key):
            return cls
     """
    node = extract_node(class_src)
    return node.infer(context=context)



if sys.version_info[:2] == (3, 9):
    MANAGER.register_transform(
        nodes.Name, inference_tip(infer_type_sub), _looks_like_type_subscript
    )