class A(object):
    def __iadd__(self, other): return NotImplemented
    def __add__(self, other): return NotImplemented
A() + A()  # inferred: Uninferable
