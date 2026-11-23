# Test function with a single return that always executes.
def f():
    return 1

f()  # inferred: Const(1)
