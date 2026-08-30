# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from astroid import nodes
from astroid.brain.helpers import register_module_extender
from astroid.builder import AstroidBuilder
from astroid.manager import AstroidManager


def decimal_transform() -> nodes.Module:
    """The _decimal module is not always available and the _pydecimal fallback can't be inferred."""
    return AstroidBuilder(AstroidManager()).string_build("from _pydecimal import *")


def register(manager: AstroidManager) -> None:
    try:
        import _decimal  # pylint: disable=unused-import,import-outside-toplevel
    except ImportError:
        register_module_extender(manager, "decimal", decimal_transform)
