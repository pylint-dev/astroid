# Test that constraint is satisfied when computing the object's
# method resolution order raises an MRO error.
class A():
    pass

class B(A, A):
    pass

x = B()

if isinstance(x, A):
    # +2: inferred: Instance(isinstance_mro_error.B)
    # +1: inferred._proxied: ClassDef(isinstance_mro_error.B)
    x
