try:
    1/0
except ZeroDivisionError as exc:
    pass
except ValueError as exc:
    exc  # inferred: ExceptionInstance(builtins.ValueError)
