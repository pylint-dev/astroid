class Bar(type):
    pass
mainbar = Bar("Bar", tuple(), {})
isinstance(mainbar, object)  # inferred: Const(True)
