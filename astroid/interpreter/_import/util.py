# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import pathlib
import sys
from functools import lru_cache
from importlib._bootstrap_external import _NamespacePath
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
    last_submodule_search_locations: _NamespacePath | None = None
    for component in modname.split("."):
        processed_components.append(component)
        working_modname = ".".join(processed_components)
        try:
            # the path search is not recursive, so that's why we are iterating
            # and using the last parent path
            found_spec = _find_spec_from_path(
                working_modname, last_submodule_search_locations
            )
        except ValueError:
            # executed .pth files may not have __spec__
            return True
        except KeyError:
            # Intermediate steps might raise KeyErrors
            # https://github.com/python/cpython/issues/93334
            # TODO: update if fixed in importlib
            # For tree a > b > c.py
            # >>> from importlib.machinery import PathFinder
            # >>> PathFinder.find_spec('a.b', ['a'])
            # KeyError: 'a'

            # Repair last_submodule_search_locations
            if last_submodule_search_locations:
                assumed_location = (
                    # pylint: disable=unsubscriptable-object
                    pathlib.Path(last_submodule_search_locations[-1])
                    / component
                )
                last_submodule_search_locations.append(str(assumed_location))
            continue

        # Update last_submodule_search_locations
        if found_spec and found_spec.submodule_search_locations:
            last_submodule_search_locations = found_spec.submodule_search_locations

    if found_spec is None:
        return False

    return found_spec.origin is None
