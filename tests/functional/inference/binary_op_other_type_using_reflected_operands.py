class A(object):
    def __radd__(self, other):
        return other + 42
A() + 1  # inferred: Uninferable
1 + A()  # inferred: Const(43)
