# ``args`` is not a known empty tuple: unpacking it cannot be checked.
try:
    pass
except ValueError as err:
    err.args  # inferred: Instance(builtins.tuple)
