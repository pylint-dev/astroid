class A(object):
    def __add__(self, other): return NotImplemented
class B(object):
    def __radd__(self, other): return NotImplemented
A() + B()  # inferred: Uninferable
