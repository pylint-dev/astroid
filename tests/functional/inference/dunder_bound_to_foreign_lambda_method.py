# ``bool()`` and ``not`` look up ``__bool__`` through ``_is_property`` too.
class A:
    f = lambda self: False

class B:
    __bool__ = A().f

bool(B())  # inferred: Const(False)
not B()  # inferred: Const(True)
