class A(object):
    def test(self): pass
class B(A):
    def test_b(self): pass
class C(A): pass
class E(C, B):
    def test_e(self): pass

hasattr(A(), 'test')  # inferred: Const(True)
hasattr(A, 'test')  # inferred: Const(True)
hasattr(E(), 'test_b')  # inferred: Const(True)
hasattr(E(), 'test')  # inferred: Const(True)

class X(object):
    def test(self):
        hasattr(self, 'test')  # inferred: Const(True)
