# Test constraint for an object whose type is a strict subtype of the checked type.
class A:
    pass

class B(A):
    pass

x = B()

if isinstance(x, A):
    # +2: inferred: Instance(isinstance_subtype.B)
    # +1: inferred._proxied: ClassDef(isinstance_subtype.B)
    x
