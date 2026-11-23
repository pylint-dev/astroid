class MyClass:
    pass

MyClass().__lt__(None) if "__lt__" != "__hash__" else MyClass().__lt__()  # inferred: Uninferable
