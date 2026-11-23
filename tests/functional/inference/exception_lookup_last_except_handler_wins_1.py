try:
    1/0
except ValueError as exc:
    pass
try:
    1/0
except OSError as exc:
    exc  # inferred: ExceptionInstance(builtins.OSError)
