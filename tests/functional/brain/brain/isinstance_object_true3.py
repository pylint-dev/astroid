class Bar(object):
    pass
isinstance(Bar(), Bar)  # inferred: Const(True)
