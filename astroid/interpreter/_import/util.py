# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

from importlib.util import _find_spec_from_path


def is_namespace(modname: str) -> bool:
    found_spec = None

    # find_spec() attempts to import parent packages when given dotted paths.
    # That's unacceptable here, so we fallback to _find_spec_from_path(), which does
    # not, but requires instead that each single parent ('astroid', 'nodes', etc.)
    # be specced from left to right.
    working_modname = ""
    last_parent = None
    for component in modname.split("."):
        if working_modname:
            working_modname += "." + component
        else:
            # First component
            working_modname = component
        try:
            found_spec = _find_spec_from_path(working_modname, last_parent)
        except (
            AttributeError,  # TODO: remove AttributeError when 3.7+ is min
            ValueError,
        ):
            # executed .pth files may not have __spec__
            return True
        last_parent = working_modname

    if found_spec is None:
        return
    # origin can be either a string on older Python versions
    # or None in case it is a namespace package:
    # https://github.com/python/cpython/pull/5481
    return found_spec.origin in {None, "namespace"}
