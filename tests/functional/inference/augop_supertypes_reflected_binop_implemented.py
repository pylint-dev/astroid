class A(object):
    def __iadd__(self, other): return NotImplemented
class B(A):
    def __radd__(self, other): return other
a = A()
a += B()  # inferred: Instance(augop_supertypes_reflected_binop_implemented.A)
