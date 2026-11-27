getattr(1, 'ala', None)  # inferred: Const(None)
getattr(int, 'bala', int)  # inferred: ClassDef(builtins.int)
getattr(int, 'bala', getattr(int, 'portocala', None))  # inferred: Const(None)
