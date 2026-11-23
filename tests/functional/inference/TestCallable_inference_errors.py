from unknown import unknown
callable(unknown)  # inferred: Uninferable
def test():
    return unknown
callable(test())  # inferred: Uninferable
