class A(object):
    pass
class B(A):
    def __radd__(self, other):
         return other
A() + B()  # inferred: Instance(binop_supertype.A)
