# Copyright (c) 2016, 2018 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2021 Pierre Sassoulas <pierre.sassoulas@gmail.com>
# Copyright (c) 2021 Daniël van Noord <13665637+DanielNoord@users.noreply.github.com>
# Copyright (c) 2021 Neil Girdhar <mistersheik@gmail.com>


from importlib import abc, util

from astroid.const import PY36


def _is_old_setuptools_namespace_package(modname: str) -> bool:
    """Check for old types of setuptools namespace packages.

    See https://setuptools.pypa.io/en/latest/pkg_resources.html and
    https://packaging.python.org/en/latest/guides/packaging-namespace-packages/

    Because pkg_resources is slow to import we only do so if explicitly necessary.
    """
    try:
        import pkg_resources  # pylint: disable=import-outside-toplevel
    except ImportError:
        return False

    return (
        hasattr(pkg_resources, "_namespace_packages")
        and modname in pkg_resources._namespace_packages  # type: ignore[attr-defined]
    )


def is_namespace(modname: str) -> bool:
    """Determine whether we encounter a namespace package."""
    if PY36:
        # On Python 3.6 an AttributeError is raised when a package
        # is lacking a __path__ attribute and thus is not a
        # package.
        try:
            spec = util.find_spec(modname)
        except (AttributeError, ValueError):
            return _is_old_setuptools_namespace_package(modname)
    else:
        try:
            spec = util.find_spec(modname)
        except ValueError:
            return _is_old_setuptools_namespace_package(modname)

    # If there is no spec or origin this is a namespace package
    # See: https://docs.python.org/3/library/importlib.html#importlib.machinery.ModuleSpec.origin
    # We assume builtin packages are never namespace
    if not spec or not spec.origin or spec.origin == "built-in":
        return False

    # If there is no loader the package is namespace
    # See https://docs.python.org/3/library/importlib.html#importlib.abc.PathEntryFinder.find_loader
    if not spec.loader:
        return True
    # This checks for _frozen_importlib.FrozenImporter, which does not inherit from InspectLoader
    if hasattr(spec.loader, "_ORIGIN") and spec.loader._ORIGIN == "frozen":
        return False
    # Other loaders are namespace packages
    if not isinstance(spec.loader, abc.InspectLoader):
        return True

    # TODO: We should find a way to check this without importing pkg_resources
    return _is_old_setuptools_namespace_package(modname)
