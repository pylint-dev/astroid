# Test constraint for an object that inherits from parent classes
# in diamond inheritance.
class A():
    pass

class B(A):
    pass

class C(A):
    pass

class D(B, C):
    pass

x = D()

if isinstance(x, D):
    # +2: inferred: Instance(isinstance_diamond_inheritance.D)
    # +1: inferred._proxied: ClassDef(isinstance_diamond_inheritance.D)
    x

if isinstance(x, B):
    # +2: inferred: Instance(isinstance_diamond_inheritance.D)
    # +1: inferred._proxied: ClassDef(isinstance_diamond_inheritance.D)
    x

if isinstance(x, C):
    # +2: inferred: Instance(isinstance_diamond_inheritance.D)
    # +1: inferred._proxied: ClassDef(isinstance_diamond_inheritance.D)
    x

if isinstance(x, A):
    # +2: inferred: Instance(isinstance_diamond_inheritance.D)
    # +1: inferred._proxied: ClassDef(isinstance_diamond_inheritance.D)
    x
