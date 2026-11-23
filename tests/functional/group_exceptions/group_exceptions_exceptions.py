try:
    raise ExceptionGroup('', [TypeError(), TypeError()])
except ExceptionGroup as eg:
    eg.exceptions  # inferred: Tuple(())
