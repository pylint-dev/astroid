try:
    raise ImportError("a")
except ImportError as err:
   err.name  # inferred: Const('')
   err.path  # inferred: Const('')
