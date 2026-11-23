# PyPy has its own _ctypes module, written in python: astroid reads the
# members of _CData from its source instead of not knowing them.
import ctypes
x=ctypes.c_float(1.0)
x._objects  # inferred: Const(None)
