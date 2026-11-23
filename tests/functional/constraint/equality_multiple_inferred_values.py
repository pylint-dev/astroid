# Test that an equality constraint with a name operand filters every
# inferred value.
#
# Checking a value must not pollute the inference context used to check
# the following ones.
y = 1

def f(cond):
    x = 1 if cond else 2
    if x == y:
        return (
            x  # inferred: Const(1)
        )
