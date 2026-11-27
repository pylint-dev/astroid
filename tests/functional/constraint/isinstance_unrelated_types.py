# Test constraint for an object whose type is not related to the checked type.
class A:
    pass

class B:
    pass

x = A()

if isinstance(x, B):
    x  # inferred: Uninferable
