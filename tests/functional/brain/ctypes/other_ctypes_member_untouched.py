# Test that other ctypes members, which are not touched by the brain, are correctly
# inferred.
import ctypes
ctypes.ARRAY(3, 2)  # inferred: Const(6)
