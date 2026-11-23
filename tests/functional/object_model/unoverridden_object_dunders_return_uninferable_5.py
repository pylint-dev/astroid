class MyClass:
    pass

MyClass().__gt__(None) if "__gt__" != "__hash__" else MyClass().__gt__()  # inferred: Uninferable
