class A:
    def __enter__(self):
        return self
class B:
    __enter__ = lambda self: self
class C:
    @property
    def a(self): return A()
    def __enter__(self):
        return self.a
with A() as a:
    a  # inferred: Instance(context_call_for_context_managers.A)
with B() as b:
    b  # inferred: Instance(context_call_for_context_managers.B)
with C() as c:
    c  # inferred: Instance(context_call_for_context_managers.A)
