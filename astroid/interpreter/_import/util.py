# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

import sys
from functools import lru_cache
from importlib.util import _find_spec_from_path


@lru_cache(maxsize=4096)
def is_namespace(modname: str) -> bool:
    if modname in sys.builtin_module_names:
        return False

    found_spec = None

    # find_spec() attempts to import parent packages when given dotted paths.
    # That's unacceptable here, so we fallback to _find_spec_from_path(), which does
    # not, but requires instead that each single parent ('astroid', 'nodes', etc.)
    # be specced from left to right.
    components = modname.split(".")
    for i in range(1, len(components) + 1):
        working_modname = ".".join(components[:i])
        try:
            # Search under the highest package name
            # Only relevant if package not already on sys.path
            # See https://github.com/python/cpython/issues/89754 for reasoning
            # Otherwise can raise bare KeyError: https://github.com/python/cpython/issues/93334
            found_spec = _find_spec_from_path(working_modname, components[0])
        except ValueError:
            # executed .pth files may not have __spec__
            return True

    if found_spec is None:
        return False

    return found_spec.origin is None
