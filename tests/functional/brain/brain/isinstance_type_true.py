class Bar(type):
    pass
mainbar = Bar("Bar", tuple(), {})
isinstance(mainbar, type)  # inferred: Const(True)
