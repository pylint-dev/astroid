# Test function with a single return that only sometimes executes.
#
# Note: currently, inference doesn't handle this type of control flow
def f(x):
    if x:
        return 1

f(1)  # inferred: Const(1)
