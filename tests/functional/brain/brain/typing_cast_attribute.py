import typing
class A:
    pass

b = 42
typing.cast(A, b)  # inferred: Const(42)
