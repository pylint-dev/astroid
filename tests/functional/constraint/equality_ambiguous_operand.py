# Test that equality constraint is satisfied when the compared operand has multiple inferred values.
def f(y = 1):
    x = 3
    if x == y:
        x  # inferred: Const(3)

    if x != y:
        x  # inferred: Const(3)
