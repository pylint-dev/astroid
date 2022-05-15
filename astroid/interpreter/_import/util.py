# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import pathlib
from functools import lru_cache
from importlib.machinery import BuiltinImporter
from importlib.util import _find_spec_from_path


def _is_setuptools_namespace(location: pathlib.Path) -> bool:
    try:
        with open(location / "__init__.py", "rb") as stream:
            data = stream.read(4096)
    except OSError:
        return False
    else:
        extend_path = b"pkgutil" in data and b"extend_path" in data
        declare_namespace = (
            b"pkg_resources" in data and b"declare_namespace(__name__)" in data
        )
        return extend_path or declare_namespace


@lru_cache(maxsize=4096)
def is_namespace(modname: str) -> bool:
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
            found_spec = _find_spec_from_path(working_modname, last_parent)
        except ValueError:
            # executed .pth files may not have __spec__
            return True
        last_parent = working_modname

    if found_spec is None:
        return False

    if found_spec.loader is BuiltinImporter:
        # TODO(Py39): remove, since found_spec.origin will be "built-in"
        return False

    if found_spec.origin is None:
        return True

    if found_spec.submodule_search_locations is not None:
        for search_location in found_spec.submodule_search_locations:
            if any(
                _is_setuptools_namespace(directory)
                for directory in pathlib.Path(search_location).iterdir()
                if directory.is_dir()
            ):
                return True

    return False
