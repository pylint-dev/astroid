class Bar(object):
    pass
isinstance(Bar(), type)  # inferred: Const(False)
