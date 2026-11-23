class A(object): pass
def test(self): return 42
f = test.__get__(A(), A)
# +2: inferred: BoundMethod(partial_descriptor_support.test)
# +1: inferred._proxied._proxied.name: 'test'
f
f()  # inferred: Const(42)
