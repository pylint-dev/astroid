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
    processed_components = []
    last_parent = None
    for component in modname.split("."):
        processed_components.append(component)
        working_modname = ".".join(processed_components)
        try:
            # the path search is not recursive, so that's why we are iterating
            # and using the last parent path
            found_spec = _find_spec_from_path(working_modname, last_parent)
        except ValueError:
            # executed .pth files may not have __spec__
            return True
        except KeyError:
            # Some homonyms might raise KeyErrors
            # https://github.com/python/cpython/issues/93334
            # TODO: update if fixed in importlib
            # For a tree a > b > a.py
            # >>> from importlib.machinery import PathFinder
            # >>> PathFinder.find_spec('a.b.a')  # same result with path='a' or 'a.b'
            # KeyError: 'a.b'
            return False
        last_parent = working_modname

    if found_spec is None:
        return False

    return found_spec.origin is None
