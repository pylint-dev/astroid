# Test that un-overridden object dunders return Uninferable when called.
class MyClass:
    pass

MyClass().__eq__(None) if "__eq__" != "__hash__" else MyClass().__eq__()  # inferred: Uninferable
