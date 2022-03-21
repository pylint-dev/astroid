# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

try:
    import pkg_resources
except ImportError:
    pkg_resources = None  # type: ignore[assignment]


def is_namespace(modname):
    return (
        pkg_resources is not None
        and hasattr(pkg_resources, "_namespace_packages")
        and modname in pkg_resources._namespace_packages
    )
