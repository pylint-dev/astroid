# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

from typing import TYPE_CHECKING

from astroid.brain.helpers import register_module_extender
from astroid.builder import AstroidBuilder
from astroid.const import PY312_PLUS
from astroid.manager import AstroidManager

if TYPE_CHECKING:
    from astroid import nodes


def datetime_transform() -> nodes.Module:
    """The datetime module was C-accelerated in Python 3.12, so use the
    Python source."""
    return AstroidBuilder(AstroidManager()).string_build("from _pydatetime import *")


def register(manager: AstroidManager) -> None:
    if PY312_PLUS:
        register_module_extender(manager, "datetime", datetime_transform)
