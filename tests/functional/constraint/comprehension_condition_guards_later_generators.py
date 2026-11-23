# Test that a generator's conditions guard the iterables of later generators.
[y for x in [None, [3]] if x is not None for y in x]  # elt.inferred: Const(3)
