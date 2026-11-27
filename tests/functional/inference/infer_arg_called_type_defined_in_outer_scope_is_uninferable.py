def outer(type):
    def inner():
        type[0]  # inferred: Uninferable
