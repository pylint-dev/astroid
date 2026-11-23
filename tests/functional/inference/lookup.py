class A(object):
    def test(self): pass
class B(A):
    def test_b(self): pass
class C(A): pass
class E(C, B):
    def test_e(self): pass

getattr(A(), 'test')  # inferred: BoundMethod(lookup.A.test)  # inferred.bound.name: 'A'
# +3: inferred: UnboundMethod(lookup.A.test)
# +2: inferred.parent: ClassDef(lookup.A)
# +1: inferred.parent.name: 'A'
getattr(A, 'test')
# +3: inferred: BoundMethod(lookup.B.test_b)
# +2: inferred._proxied._proxied.parent.name: 'B'
# +1: inferred.bound.name: 'E'
getattr(E(), 'test_b')
getattr(E(), 'test')  # inferred: BoundMethod(lookup.A.test)  # inferred.bound.name: 'E'

class X(object):
    def test(self):
        getattr(self, 'test')  # inferred: BoundMethod(lookup.X.test)  # inferred.bound.name: 'X'
