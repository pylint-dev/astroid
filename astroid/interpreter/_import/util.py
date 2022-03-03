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
