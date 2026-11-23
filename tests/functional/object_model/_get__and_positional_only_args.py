def test(self, a, b, /, c): return a + b + c
test.__get__(test)(1, 2, 3)  # inferred: Uninferable
