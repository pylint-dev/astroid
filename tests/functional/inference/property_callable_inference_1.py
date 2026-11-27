class A:
    def func(self):
        return 42
    p = property(func)
A().p  # inferred: Const(42)
