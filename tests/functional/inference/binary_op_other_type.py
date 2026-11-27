class A:
    def __add__(self, other):
        return other + 42
A() + 1  # inferred: Const(43)
1 + A()  # inferred: Uninferable
