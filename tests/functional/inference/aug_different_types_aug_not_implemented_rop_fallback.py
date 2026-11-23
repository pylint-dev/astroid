class A(object):
    def __iadd__(self, other): return NotImplemented
    def __add__(self, other): return NotImplemented
class B(object):
    def __radd__(self, other): return other
f = A()
f += B()  # inferred: Instance(aug_different_types_aug_not_implemented_rop_fallback.A)
