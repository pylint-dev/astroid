class A(object):
    def __iadd__(self, other): return NotImplemented
    def __add__(self, other): return other
class B(object): pass
f = A()
f += B()  # inferred: Instance(aug_different_types_aug_not_implemented.B)
