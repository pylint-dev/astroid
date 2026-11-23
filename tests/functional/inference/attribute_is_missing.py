class A: pass
hasattr(int, 'ala')  # inferred: Const(False)
hasattr({}, 'bala')  # inferred: Const(False)
hasattr(A(), 'portocala')  # inferred: Const(False)
