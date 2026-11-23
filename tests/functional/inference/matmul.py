class Array:
    def __matmul__(self, other):
        return 42
Array() @ Array()  # inferred: Const(42)
