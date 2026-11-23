class A(object):
    pass
class B(A):
    def __add__(self, other): return NotImplemented
B() + A()  # inferred: Uninferable
