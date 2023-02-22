import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    __import__("pkg_resources").declare_namespace(__name__)
