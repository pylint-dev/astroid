class Bar(type):
    pass
issubclass(Bar, object)  # inferred: Const(True)
