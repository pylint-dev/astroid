class BoolInvalid(object):
   __bool__ = 42
class LenInvalid(object):
   __len__ = "a"
bool(BoolInvalid())  # inferred: Uninferable
bool(LenInvalid())  # inferred: Uninferable
