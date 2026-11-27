class MyClass:
    pass

MyClass().__ne__(None) if "__ne__" != "__hash__" else MyClass().__ne__()  # inferred: Uninferable
