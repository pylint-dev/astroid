# Test that an operand of a nested boolean operation is constrained.
def f1(y, x = None):
    if y or (x is not None and x):  # test.values[1].values[1].inferred: Uninferable
        pass

def f2(y, x = 1):
    if y or (x is not None and x):  # test.values[1].values[1].inferred: Const(1) | Uninferable
        pass
