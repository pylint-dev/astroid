# Test constraint for an object whose type is equal to the checked type.
class A:
    pass

x = A()

if isinstance(x, A):
    # +2: inferred: Instance(isinstance_equal_types.A)
    # +1: inferred._proxied: ClassDef(isinstance_equal_types.A)
    x
