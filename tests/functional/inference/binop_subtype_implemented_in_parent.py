class A(object):
    def __add__(self, other): return other
class B(A): pass
B() + A()  # inferred: Instance(binop_subtype_implemented_in_parent.A)
