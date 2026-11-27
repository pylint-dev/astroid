# Test that a value assigned after the use in a loop is constrained: it has
# passed the guard on the next iteration.
def f(y, x = 1):
    while y:
        if x is None:
            break
        x  # inferred: Const(1) | Uninferable
        x = None
