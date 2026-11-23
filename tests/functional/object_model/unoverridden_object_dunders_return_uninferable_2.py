class MyClass:
    pass

# +1: inferred: Uninferable
MyClass().__hash__(None) if "__hash__" != "__hash__" else MyClass().__hash__()
