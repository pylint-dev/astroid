class A(object):
    def __add__(self, other):
        return other
class B(A):
    def __radd__(self, other):
         return NotImplemented
A() + B()  # inferred: Instance(binop_supertype_rop_not_implemented.B)
