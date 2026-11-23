# Test that all conditions apply to the element expression and that earlier
# conditions also guard later ones.
# +2: elt.inferred: Const(3)
# +1: generators[0].ifs[1].left.inferred: Const(3) | Const(4)
[x for x in [None, 3, 4] if x is not None if x == 3]
