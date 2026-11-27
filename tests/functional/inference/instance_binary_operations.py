class A(object):
    def __mul__(self, other):
        return 42
a = A()
b = A()
sub = a - b  # inferred: Uninferable
mul = a * b  # inferred: Const(42)
