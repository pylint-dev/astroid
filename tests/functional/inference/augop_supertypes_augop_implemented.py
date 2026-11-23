class A(object):
    def __iadd__(self, other): return other
class B(A): pass
a = A()
a += B()  # inferred: Instance(augop_supertypes_augop_implemented.B)
