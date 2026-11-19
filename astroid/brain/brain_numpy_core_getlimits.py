# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Astroid hooks for numpy's getlimits module.

Since NumPy 2.4, ``finfo._init`` lets ``_populate_finfo_constants``, written in
C, set most of the machine limits of a ``finfo`` instance, so the class source
no longer assigns ``eps``, ``max`` and the other constants.
"""

from typing import cast

from astroid import nodes
from astroid.manager import AstroidManager
from astroid.typing import TransformFn

# The public attributes that ``_populate_finfo_constants`` sets.
FINFO_CONSTANTS = (
    "eps",
    "max",
    "maxexp",
    "min",
    "minexp",
    "nmant",
    "precision",
    "smallest_normal",
    "smallest_subnormal",
)


def _looks_like_finfo(node: nodes.ClassDef) -> bool:
    return node.name == "finfo" and node.root().name in {
        "numpy.core.getlimits",
        "numpy._core.getlimits",
    }


def _add_finfo_constants(node: nodes.ClassDef) -> None:
    for name in FINFO_CONSTANTS:
        if name in node.instance_attrs or name in node.locals:
            continue
        node.instance_attrs[name] = [nodes.EmptyNode(parent=node)]


def register(manager: AstroidManager) -> None:
    # TransformFn also expects the optional infer_function of inference tips.
    manager.register_transform(
        nodes.ClassDef,
        cast(TransformFn[nodes.ClassDef], _add_finfo_constants),
        _looks_like_finfo,
    )
