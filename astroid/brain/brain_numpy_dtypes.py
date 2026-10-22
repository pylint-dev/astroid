# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Astroid hooks for the numpy.dtypes module.

NumPy builds the DType classes in C and attaches them to ``numpy.dtypes``
at import time (``_add_dtype_helper``), so the module's source defines none
of them and ``numpy.dtypes.StringDType`` cannot be inferred.
"""

from astroid import nodes
from astroid.brain.helpers import register_module_extender
from astroid.builder import parse
from astroid.manager import AstroidManager

# Every name ``numpy.dtypes.__all__`` holds in NumPy 2.x. ``StringDType`` is
# new in 2.0; the rest exist since 1.25. Some are aliases of each other
# (``ByteDType`` is ``Int8DType``), but which fixed-width class a C-type alias
# such as ``LongDType`` names depends on the platform, so each name gets its
# own class here.
DTYPE_CLASS_NAMES = (
    "BoolDType",
    "Int8DType",
    "ByteDType",
    "UInt8DType",
    "UByteDType",
    "Int16DType",
    "ShortDType",
    "UInt16DType",
    "UShortDType",
    "IntDType",
    "UIntDType",
    "Int32DType",
    "LongDType",
    "UInt32DType",
    "ULongDType",
    "Int64DType",
    "LongLongDType",
    "UInt64DType",
    "ULongLongDType",
    "Float16DType",
    "Float32DType",
    "Float64DType",
    "LongDoubleDType",
    "Complex64DType",
    "Complex128DType",
    "CLongDoubleDType",
    "ObjectDType",
    "BytesDType",
    "StrDType",
    "VoidDType",
    "DateTime64DType",
    "TimeDelta64DType",
    "StringDType",
)


# The DType classes do not share ``numpy.dtype``'s ``(obj, align, copy)``
# constructor. Most take no argument at all; these take one positional-only
# argument (their ``__text_signature__``), and ``StringDType`` is keyword-only.
_POSITIONAL_PARAMETER = {
    "BytesDType": "size",
    "StrDType": "size",
    "VoidDType": "length",
    "DateTime64DType": "unit",
    "TimeDelta64DType": "unit",
}

_STRING_DTYPE = """
class StringDType(numpy.dtype):
    def __init__(self, *, na_object=None, coerce=True):
        self.na_object = na_object
        self.coerce = coerce
"""


def _dtype_class(name: str) -> str:
    if name == "StringDType":
        return _STRING_DTYPE
    parameter = _POSITIONAL_PARAMETER.get(name)
    signature = f"self, {parameter}, /" if parameter else "self"
    return f"""
class {name}(numpy.dtype):
    def __init__({signature}): ...
"""


def numpy_dtypes_transform() -> nodes.Module:
    classes = "".join(_dtype_class(name) for name in DTYPE_CLASS_NAMES)
    return parse(f"import numpy\n{classes}")


def register(manager: AstroidManager) -> None:
    register_module_extender(manager, "numpy.dtypes", numpy_dtypes_transform)
