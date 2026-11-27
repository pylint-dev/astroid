class A(object):
    def spam(self): return "A"
    def foo(self): return "A"
    @staticmethod
    def static(self): pass
class B(A):
    def boo(self): return "B"
    def spam(self): return "B"
class C(A):
    def boo(self): return "C"
class E(C, B):
    def __init__(self):
        # +2: inferred: BoundMethod(super_complex_mro.B.boo) | BoundMethod(super_complex_mro.C.boo)
        # +1: inferred.bound.name: 'B' | 'C'
        super(E, self).boo
        # +2: inferred: BoundMethod(super_complex_mro.B.boo)
        # +1: inferred.bound.name: 'B'
        super(C, self).boo
        # +2: inferred: BoundMethod(super_complex_mro.A.spam) | BoundMethod(super_complex_mro.B.spam)
        # +1: inferred.bound.name: 'A' | 'B'
        super(E, self).spam
        # +2: inferred: BoundMethod(super_complex_mro.A.foo)
        # +1: inferred.bound.name: 'A'
        super(E, self).foo
        # +2: inferred: FunctionDef(super_complex_mro.A.static)
        # +1: inferred.parent.scope().name: 'A'
        super(E, self).static
