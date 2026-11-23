# Test that a nested boolean operation constrains a later operand.
def f1(x = None):
    if (x and x is None) and x:  # test.values[1].inferred: Uninferable
        pass

def f2(x = None):
    if not x and x is None or x:  # test.values[1].inferred: Uninferable
        pass
