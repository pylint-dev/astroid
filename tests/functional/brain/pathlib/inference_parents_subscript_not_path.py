# Test inference of other ``.parents`` subscripts is unaffected.
class A:
    parents = 42

c = A()
error = c.parents[:2]
error  # inferred: Uninferable
