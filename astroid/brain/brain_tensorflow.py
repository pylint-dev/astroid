"""Astroid hooks for understanding tensorflow's imports."""
from astroid import MANAGER
from astroid.exceptions import AstroidBuildingError


def _tensorflow_fail_hook(modname: str):
    parts = modname.split(".", 1)
    if parts[0] == "tensorflow":
        parts[0] = "tensorflow.python"
        return MANAGER.ast_from_module_name(".".join(parts))
    raise AstroidBuildingError(modname=modname)


MANAGER.register_failed_import_hook(_tensorflow_fail_hook)
