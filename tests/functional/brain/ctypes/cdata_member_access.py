# Test that the base members are still accessible. Each redefined ctypes type
# inherits from _SimpleCData which itself inherits from _CData. Checks that
# _CData members are accessible.
import ctypes
x=ctypes.c_float(1.0)
x._objects  # inferred: Uninferable
