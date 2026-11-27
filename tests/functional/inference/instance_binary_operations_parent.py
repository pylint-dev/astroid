class A(object):
    def __mul__(self, other):
        return 42
class B(A):
    pass
a = B()
b = B()
sub = a - b  # inferred: Uninferable
mul = a * b  # inferred: Const(42)
