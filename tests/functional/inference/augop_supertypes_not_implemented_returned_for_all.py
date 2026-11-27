class A(object):
    def __iadd__(self, other): return NotImplemented
    def __add__(self, other): return NotImplemented
class B(object):
    def __add__(self, other): return NotImplemented
a = A()
a += B()  # inferred: Uninferable
