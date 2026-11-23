from typing import cast
class A:
    pass

b = 42
cast(A, b)  # inferred: Const(42)
