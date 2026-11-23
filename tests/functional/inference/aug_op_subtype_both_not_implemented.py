class A(object):
    def __iadd__(self, other): return NotImplemented
    def __add__(self, other): return NotImplemented
class B(A):
    pass
b = B()
b+=A()  # inferred: Uninferable
