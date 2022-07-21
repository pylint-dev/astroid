'''
This is a mock of a module like Pandas, which can throw warnings for deprecated attributes
'''
import warnings


def __dir__():
    # GH43028
    # Int64Index etc. are deprecated, but we still want them to be available in the dir.
    # Remove in Pandas 2.0, when we remove Int64Index etc. from the code base.
    return list(globals().keys()) + ["Float64Index"]


def __getattr__(name):
    if name == "Float64Index":
        warnings.warn("This is what pandas would do", FutureWarning, stacklevel=2)
        return 5
    raise AttributeError(f"module 'pandas' has no attribute '{name}'")


__all__ = ["Float64Index"]  # pylint: disable=E0603
__doc__ = ""
