class A(object): pass
class B(A):
    def __add__(self, other): return other
B() + A()  # inferred: Instance(binop_subtype.A)
