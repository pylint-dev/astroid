# +1: generators[1].iter.args[0].inferred: Const(1)
[y for x in [None, 1] if x is not None for y in make_iter(x)]
