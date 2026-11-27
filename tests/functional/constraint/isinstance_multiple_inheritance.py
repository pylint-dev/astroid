# Test constraint for an object that inherits from more than one parent class.
class A:
    pass

class B:
    pass

class C(A, B):
    pass

x = C()

if isinstance(x, C):
    # +2: inferred: Instance(isinstance_multiple_inheritance.C)
    # +1: inferred._proxied: ClassDef(isinstance_multiple_inheritance.C)
    x

if isinstance(x, A):
    # +2: inferred: Instance(isinstance_multiple_inheritance.C)
    # +1: inferred._proxied: ClassDef(isinstance_multiple_inheritance.C)
    x

if isinstance(x, B):
    # +2: inferred: Instance(isinstance_multiple_inheritance.C)
    # +1: inferred._proxied: ClassDef(isinstance_multiple_inheritance.C)
    x
