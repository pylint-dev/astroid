class MyClass:
    pass

MyClass().__le__(None) if "__le__" != "__hash__" else MyClass().__le__()  # inferred: Uninferable
