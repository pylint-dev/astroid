# Test that a value assigned between a guard and the use is not constrained.
def f1(x = 1):
    if x is None:
        return
    x = None
    x  # inferred: Const(None)

def f2(y, x = None):
    if x is None:
        return
    if y:
        x = None
    x  # inferred: Const(None) | Uninferable
