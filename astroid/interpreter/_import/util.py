# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

from importlib.util import find_spec


def is_namespace(modname):
    try:
        found_spec = find_spec(modname)
    except ValueError:
        # execution of .pth files may not have __spec__
        return True
    if found_spec is None:
        return
    # origin can be either a string on older Python versions
    # or None in case it is a namespace package:
    # https://github.com/python/cpython/pull/5481
    return found_spec.origin in {None, "namespace"}
