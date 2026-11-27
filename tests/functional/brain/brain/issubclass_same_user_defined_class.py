class Bar(object):
    pass
issubclass(Bar, Bar)  # inferred: Const(True)
