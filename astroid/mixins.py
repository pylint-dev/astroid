# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

"""This module contains some mixins for the different nodes.
"""

import warnings

from astroid.nodes._base_nodes import AssignTypeMixin, FilterStmtsMixin, ImportFromMixin
from astroid.nodes._base_nodes import MultiLineBlockNode as MultiLineBlockMixin
from astroid.nodes._base_nodes import MultiLineWithElseBlockNode as BlockRangeMixIn
from astroid.nodes._base_nodes import NoChildrenMixin, ParentAssignTypeMixin

__all__ = (
    "AssignTypeMixin",
    "BlockRangeMixIn",
    "FilterStmtsMixin",
    "ImportFromMixin",
    "MultiLineBlockMixin",
    "NoChildrenMixin",
    "ParentAssignTypeMixin",
)

warnings.warn(
    "The 'astroid.mixins' module is deprecated and will become private in astroid 3.0.0",
    DeprecationWarning,
)
