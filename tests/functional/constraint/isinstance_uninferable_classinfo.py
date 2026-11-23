# Test that constraint is satisfied when `isinstance` is called with
# uninferable classinfo.
def f(classinfo):
    x = 3

    if isinstance(x, classinfo):
        x  # inferred: Const(3)
