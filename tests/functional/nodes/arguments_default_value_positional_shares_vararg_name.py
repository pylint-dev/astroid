# The default of a positional argument shadowed by ``*args`` is still found.
def f(y=1, *y): ...  # args.default_value('y').value: 1
