# Test that comprehension conditions constrain a name used inside an inner
# comprehension.
# +2: elt.elt.inferred: Const(1)
# +1: elt.generators[0].iter.inferred: List([1])
[[y for y in x] for x in [None, [1]] if x is not None]
