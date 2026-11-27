# Test that constraint does not apply when `isinstance` is called
# with keyword arguments.
x = 3

if isinstance(object=x, classinfo=str):
    x  # inferred: Const(3)

if isinstance(x, str, object=x, classinfo=str):
    x  # inferred: Const(3)
