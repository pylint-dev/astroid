class A(object):
    def __iadd__(self, other): return other
f = A()
f += A()  # inferred: Instance(aug_op_same_type_aug_implemented.A)
