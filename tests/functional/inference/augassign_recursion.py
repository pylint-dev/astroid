# Make sure inference doesn't throw a RecursionError.
#
# Regression test for augmented assign dropping context.path
# causing recursion errors
def rec():
    a = 0
    a += rec()
    return a
rec()  # inferred: Uninferable
