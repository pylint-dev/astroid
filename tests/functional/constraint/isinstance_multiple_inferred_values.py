# Test that an isinstance() constraint filters every inferred value.
#
# Checking a value must not pollute the inference context used to check
# the following ones.
def f(y):
    x = 2 if y else "a"
    if isinstance(x, int):
        return (
            x  # inferred: Const(2)
        )
