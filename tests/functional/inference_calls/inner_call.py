# Test function where return value is the result of a separate function call.
def f():
    return g()

def g():
    return 1

f()  # inferred: Const(1)
