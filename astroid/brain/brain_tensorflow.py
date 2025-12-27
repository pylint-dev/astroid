# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt
"""Astroid hooks for understanding tensorflow's imports."""
from astroid import MANAGER
from astroid.exceptions import AstroidBuildingError


def _tensorflow_fail_hook(modname: str):
    parts = modname.split(".", 1)
    fallbacks = ("python", "_api.v2")
    if parts[0] == "tensorflow":
        for fallback in fallbacks:
            if parts[1].startswith(fallbacks):
                continue
            try:
                return MANAGER.ast_from_module_name(f"tensorflow.{fallback}.{parts[1]}")
            except AstroidBuildingError:
                continue
    raise AstroidBuildingError(modname=modname)


MANAGER.register_failed_import_hook(_tensorflow_fail_hook)
