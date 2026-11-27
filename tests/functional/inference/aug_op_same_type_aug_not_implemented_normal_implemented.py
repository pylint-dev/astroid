class A(object):
    def __iadd__(self, other): return NotImplemented
    def __add__(self, other): return 42
f = A()
f += A()  # inferred: Const(42)
