class A:
    p = property(lambda self: 42)
A().p  # inferred: Const(42)
