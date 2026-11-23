# Test that constraint does not apply when `isinstance` is called
# with more than two positional arguments.
x = 3

if isinstance(x, str, bool):
    x  # inferred: Const(3)
