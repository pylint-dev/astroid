# Test function where return value is the result of a separate function call,
# with a dynamic value passed to the inner function.
#
# Currently, this is Uninferable.
def f(x):
    return g(x)

def g(y):
    return y + 2

f(1)  # inferred: Uninferable
