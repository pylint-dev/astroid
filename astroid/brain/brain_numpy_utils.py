# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Different utilities for the numpy brains."""

from __future__ import annotations

from astroid import nodes
from astroid.builder import extract_node
from astroid.context import InferenceContext


def infer_numpy_name(
    sources: dict[str, str], node: nodes.Name, context: InferenceContext | None = None
):
    extracted_node = extract_node(sources[node.name])
    return extracted_node.infer(context=context)


def infer_numpy_attribute(
    sources: dict[str, str],
    node: nodes.Attribute,
    context: InferenceContext | None = None,
):
    extracted_node = extract_node(sources[node.attrname])
    return extracted_node.infer(context=context)


def _is_a_numpy_module(node: nodes.Name) -> bool:
    """
    Returns True if the node is a representation of a numpy module.

    For example in :
        import numpy as np
        x = np.linspace(1, 2)
    The node <Name.np> is a representation of the numpy module.

    :param node: node to test
    :return: True if the node is a representation of the numpy module.
    """
    module_nickname = node.name
    potential_import_target = [
        x for x in node.lookup(module_nickname)[1] if isinstance(x, nodes.Import)
    ]
    return any(
        ("numpy", module_nickname) in target.names or ("numpy", None) in target.names
        for target in potential_import_target
    )


def member_name_looks_like_numpy_member(
    member_names: frozenset[str], node: nodes.Name
) -> bool:
    """
    Returns True if the Name node's name matches a member name from numpy
    """
    return node.name in member_names and node.root().name.startswith("numpy")


def attribute_name_looks_like_numpy_member(
    member_names: frozenset[str], node: nodes.Attribute
) -> bool:
    """
    Returns True if the Attribute node's name matches a member name from numpy
    """
    return (
        node.attrname in member_names
        and isinstance(node.expr, nodes.Name)
        and _is_a_numpy_module(node.expr)
    )
