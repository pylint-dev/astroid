class MyClass:
    def __hash__(self, *args):
        return 42

MyClass().__hash__()  # inferred: Const(42)
