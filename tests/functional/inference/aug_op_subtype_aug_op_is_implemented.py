class A(object):
    def __iadd__(self, other): return 42
class B(A):
    pass
b = B()
b+=A()  # inferred: Const(42)
