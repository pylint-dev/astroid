# Test that comprehension conditions constrain a name nested inside a call.
[f(x) for x in [None, 1] if x is not None]  # elt.args[0].inferred: Const(1)
