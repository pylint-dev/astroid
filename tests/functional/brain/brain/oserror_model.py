try:
    1/0
except OSError as exc:
    exc  # inferred: ExceptionInstance(builtins.OSError)  # inferred.igetattr(strerror): Const('')
