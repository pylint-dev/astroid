class A(object):
    def __iadd__(self, other): return other
class B(object): pass
f = A()
f += B()  # inferred: Instance(aug_different_types_augop_implemented.B)
