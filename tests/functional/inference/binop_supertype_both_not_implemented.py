class A(object):
    def __add__(self): return NotImplemented
class B(A):
    def __radd__(self, other):
         return NotImplemented
A() + B()  # inferred: Uninferable
