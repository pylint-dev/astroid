class A(object):
    def __add__(self, other):
        return NotImplemented
class B(object):
    def __radd__(self, other):
        return other
A() + B()  # inferred: Instance(binop_different_types_normal_not_implemented_and_reflected.A)
