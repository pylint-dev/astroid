# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Different utilities for the numpy brains."""

from __future__ import annotations

import re
from functools import lru_cache
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as distribution_version

from astroid import nodes
from astroid.builder import extract_node
from astroid.context import InferenceContext

# Subscripting a scalar type, as in ``np.float64[int]``, requires the
# ``__class_getitem__`` numpy defines from version 1.20 onwards.
NUMPY_TYPE_HINTS_SUPPORT = (1, 20)
NUMPY_2 = (2,)

CLASS_GETITEM_SRC = """
        @classmethod
        def __class_getitem__(cls, value):
            return cls
"""

_LEADING_DIGITS = re.compile(r"\d+")


def _parse_version(raw_version: str) -> tuple[int, ...] | None:
    """Turn a numpy version string into a tuple of integers.

    Everything from the first non numeric component onwards is dropped, so
    ``"2.0.0rc1"`` and ``"2.0.0.dev0+g1234"`` are both read as ``(2, 0, 0)``.
    Returns None if no leading numeric component can be found.
    """
    parsed = []
    for part in raw_version.split("."):
        match = _LEADING_DIGITS.match(part)
        if match is None:
            break
        parsed.append(int(match.group()))
    return tuple(parsed) or None


@lru_cache(maxsize=1)
def numpy_version() -> tuple[int, ...] | None:
    """Return the version of the installed numpy, or None if it is unknown.

    The version is read from the distribution metadata so that numpy does
    not have to be imported. None is returned when numpy is not installed
    or when its version cannot be parsed; callers then assume the most
    recent numpy API.
    """
    try:
        raw_version = distribution_version("numpy")
    except PackageNotFoundError:
        return None
    return _parse_version(raw_version)


def numpy_2_or_later() -> bool:
    """Whether the installed numpy is version 2 or later, or unknown."""
    version = numpy_version()
    return version is None or version >= NUMPY_2


def numpy_supports_type_hints() -> bool:
    """Whether the installed numpy defines ``__class_getitem__``, or is unknown."""
    version = numpy_version()
    return version is None or version >= NUMPY_TYPE_HINTS_SUPPORT


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
