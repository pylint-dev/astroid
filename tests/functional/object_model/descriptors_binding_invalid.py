class A: pass
def test(self): return 42
test.__get__()()  # inferred: InferenceError
test.__get__(2, 3, 4)  # inferred: InferenceError
