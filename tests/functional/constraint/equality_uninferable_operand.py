# Test that equality constraint is satisfied when either operand is uninferable.
def f1(x):
    if x == 3:
        x  # inferred: Uninferable

    if x != 3:
        x  # inferred: Uninferable

def f2(y):
    x = 3
    if x == y:
        x  # inferred: Const(3)

    if x != y:
        x  # inferred: Const(3)
