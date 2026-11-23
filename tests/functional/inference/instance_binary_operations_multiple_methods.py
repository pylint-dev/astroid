class A(object):
    def __mul__(self, other):
        return 42
class B(A):
    def __mul__(self, other):
        return [42]
a = B()
b = B()
sub = a - b  # inferred: Uninferable
mul = a * b  # inferred: List([42])
