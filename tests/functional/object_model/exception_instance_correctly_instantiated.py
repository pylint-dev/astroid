try:
    raise ImportError("a")
except ImportError as err:
   # +2: inferred: ExceptionInstance(builtins.ImportError)
   # +1: inferred.igetattr(__class__): ClassDef(builtins.ImportError)
   err
