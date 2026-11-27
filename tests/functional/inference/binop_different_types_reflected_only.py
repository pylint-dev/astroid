class A(object):
    pass
class B(object):
    def __radd__(self, other):
        return other
A() + B()  # inferred: Instance(binop_different_types_reflected_only.A)
