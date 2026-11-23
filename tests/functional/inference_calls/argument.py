# Test function whose return value uses its arguments.
def f(x, y):
    return x + y

f(1, 2)  # inferred: Const(3)
