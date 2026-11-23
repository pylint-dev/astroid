class A(object):
    def __iadd__(self, other): return NotImplemented
    def __add__(self, other): return other
class B(A):
    def __radd__(self, other): return NotImplemented

a = A()
a += B()  # inferred: Instance(augop_supertypes_normal_binop_implemented.B)
