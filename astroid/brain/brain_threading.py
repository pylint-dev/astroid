# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

from typing import TYPE_CHECKING

from astroid.brain.helpers import register_module_extender
from astroid.builder import parse

if TYPE_CHECKING:
    from astroid import nodes
    from astroid.manager import AstroidManager


def _thread_transform() -> nodes.Module:
    return parse(
        """
    class lock(object):
        def acquire(self, blocking=True, timeout=-1):
            return False
        def release(self):
            pass
        def __enter__(self):
            return True
        def __exit__(self, *args):
            pass
        def locked(self):
            return False

    def Lock(*args, **kwargs):
        return lock()
    """
    )


def register(manager: AstroidManager) -> None:
    register_module_extender(manager, "threading", _thread_transform)
