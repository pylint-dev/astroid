# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import TYPE_CHECKING

from astroid.exceptions import InferenceError
from astroid.manager import AstroidManager
from astroid.nodes.scoped_nodes import Module

if TYPE_CHECKING:
    from astroid.nodes.node_ng import NodeNG


def register_module_extender(
    manager: AstroidManager, module_name: str, get_extension_mod: Callable[[], Module]
) -> None:
    def transform(node: Module) -> None:
        extension_module = get_extension_mod()
        for name, objs in extension_module.locals.items():
            node.locals[name] = objs
            for obj in objs:
                if obj.parent is extension_module:
                    obj.parent = node

    manager.register_transform(Module, transform, lambda n: n.name == module_name)


# Brains that always need to be registered at astroid startup. They target
# universal constructs (builtins like ``super``/``len``/``isinstance`` and the
# ``type`` name reference) that aren't gated by any user-visible import.
_EAGER_BRAINS: tuple[str, ...] = (
    "brain_builtin_inference",
    "brain_type",
)

# Mapping from a module-name trigger to the brain modules that should be
# registered when astroid encounters that module. The trigger is matched
# against the full dotted name and against every parent prefix, so
# ``numpy.core.einsumfunc`` triggers the ``numpy`` entry too.
_LAZY_BRAINS: dict[str, tuple[str, ...]] = {
    "argparse": ("brain_argparse",),
    "attr": ("brain_attrs",),
    "attrs": ("brain_attrs",),
    "boto3": ("brain_boto3",),
    "collections": ("brain_collections", "brain_namedtuple_enum"),
    "crypt": ("brain_crypt",),
    "ctypes": ("brain_ctypes",),
    "curses": ("brain_curses",),
    "dataclasses": ("brain_dataclasses",),
    "datetime": ("brain_datetime",),
    "dateutil": ("brain_dateutil",),
    "enum": ("brain_namedtuple_enum",),
    "functools": ("brain_functools",),
    "gi": ("brain_gi",),
    "hashlib": ("brain_hashlib",),
    "http": ("brain_http",),
    "hypothesis": ("brain_hypothesis",),
    "io": ("brain_io",),
    "mechanize": ("brain_mechanize",),
    "multiprocessing": ("brain_multiprocessing",),
    "numpy": (
        "brain_numpy_core_einsumfunc",
        "brain_numpy_core_fromnumeric",
        "brain_numpy_core_function_base",
        "brain_numpy_core_multiarray",
        "brain_numpy_core_numeric",
        "brain_numpy_core_numerictypes",
        "brain_numpy_core_umath",
        "brain_numpy_ma",
        "brain_numpy_ndarray",
        "brain_numpy_random_mtrand",
    ),
    "pathlib": ("brain_pathlib",),
    "pkg_resources": ("brain_pkg_resources",),
    "py": ("brain_pytest",),
    "pytest": ("brain_pytest",),
    "PyQt4": ("brain_qt",),
    "PyQt5": ("brain_qt",),
    "PyQt6": ("brain_qt",),
    "PySide": ("brain_qt",),
    "PySide2": ("brain_qt",),
    "PySide6": ("brain_qt",),
    "random": ("brain_random",),
    "re": ("brain_re",),
    "regex": ("brain_regex",),
    "responses": ("brain_responses",),
    "scipy": ("brain_scipy_signal",),
    "signal": ("brain_signal",),
    "six": ("brain_six",),
    "sqlalchemy": ("brain_sqlalchemy",),
    "ssl": ("brain_ssl",),
    "statistics": ("brain_statistics",),
    "subprocess": ("brain_subprocess",),
    "threading": ("brain_threading",),
    "typing": ("brain_typing", "brain_namedtuple_enum"),
    "unittest": ("brain_unittest",),
    "uuid": ("brain_uuid",),
}

_loaded_brain_names: set[str] = set()


def _load_brain(manager: AstroidManager, brain_name: str) -> None:
    if brain_name in _loaded_brain_names:
        return
    _loaded_brain_names.add(brain_name)
    mod = importlib.import_module(f"astroid.brain.{brain_name}")
    mod.register(manager)


def load_brains_for_modname(manager: AstroidManager, modname: str | None) -> None:
    """Register any deferred brains targeting *modname* or any parent of it.

    Called from ``AstroidManager.ast_from_module_name`` and from
    ``AstroidBuilder._post_build`` so that a brain becomes active the first
    time astroid sees its target module being imported or resolved.
    """
    if not modname:
        return
    parts = modname.split(".")
    for i in range(len(parts), 0, -1):
        for brain_name in _LAZY_BRAINS.get(".".join(parts[:i]), ()):
            if brain_name not in _loaded_brain_names:
                _load_brain(manager, brain_name)


def register_brains(manager: AstroidManager) -> None:
    """Register the eager brains and reset lazy-brain tracking.

    Lazy brains register themselves the first time astroid encounters a
    module they target (see :func:`load_brains_for_modname`).
    """
    _loaded_brain_names.clear()
    for brain_name in _EAGER_BRAINS:
        _load_brain(manager, brain_name)


def register_all_brains(manager: AstroidManager) -> None:
    """Eagerly register every brain at once.

    Equivalent to the pre-lazy-loading behaviour: useful for tests that
    want every transform installed up front. Most callers should prefer
    :func:`register_brains` instead, which sets up lazy loading.
    """
    register_brains(manager)
    for brains in _LAZY_BRAINS.values():
        for brain_name in brains:
            if brain_name not in _loaded_brain_names:
                _load_brain(manager, brain_name)


def is_class_var(node: NodeNG) -> bool:
    """Return True if node is a ClassVar, with or without subscripting."""
    try:
        inferred = next(node.infer())
    except (InferenceError, StopIteration):
        return False

    return getattr(inferred, "name", "") == "ClassVar"
