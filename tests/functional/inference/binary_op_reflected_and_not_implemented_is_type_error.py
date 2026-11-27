class A(object):
    def __radd__(self, other): return NotImplemented

1 + A()  # inferred: Uninferable
