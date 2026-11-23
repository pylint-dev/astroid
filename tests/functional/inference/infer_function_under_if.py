if 1 in [1]:
    def func():
        return 42
else:
    def func():
        return False

func()  # inferred: Const(42) | Const(False)
