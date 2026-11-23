# Test function where return value is the result of a separate function call,
# with a constant value passed to the inner function.
def f():
    return g(1)

def g(y):
    return y + 2

f()  # inferred: Const(3)
