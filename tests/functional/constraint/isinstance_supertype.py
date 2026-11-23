# Test constraint for an object whose type is a strict supertype of the checked type.
class A:
    pass

class B(A):
    pass

x = A()

if isinstance(x, B):
    x  # inferred: Uninferable
