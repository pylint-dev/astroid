# A user-defined __str__ must never be executed during inference.
class StrWillFail:
    def __str__(self):
        raise RuntimeError

str(StrWillFail())  # inferred: Const('')
