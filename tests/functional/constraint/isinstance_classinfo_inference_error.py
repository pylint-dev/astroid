# Test that constraint is satisfied when `isinstance` is called with
# classinfo that raises an inference error.
x = 3

if isinstance(x, undefined_type):
    x  # inferred: Const(3)
