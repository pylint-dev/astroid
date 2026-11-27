# Test correct handling on list multiplied by int when there are more than one.
from ctypes import c_int
seq = [c_int()] * 4  # inferred-type: List  # inferred.itered().__len__(): 4
