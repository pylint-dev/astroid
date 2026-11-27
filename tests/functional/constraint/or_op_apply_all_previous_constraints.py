# Test that constraints from all preceding operands in an `or` operation apply.
def f1(x = None):
    if x is None or x == 1 or x:  # test.values[2].inferred: Uninferable
        pass

def f2(x = 1):
    if x is None or x == 1 or x:  # test.values[2].inferred: Uninferable
        pass

def f3(x = 3):
    if x is None or x == 1 or x:  # test.values[2].inferred: Const(3) | Uninferable
        pass
