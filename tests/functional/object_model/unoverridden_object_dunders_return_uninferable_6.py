class MyClass:
    pass

MyClass().__ge__(None) if "__ge__" != "__hash__" else MyClass().__ge__()  # inferred: Uninferable
