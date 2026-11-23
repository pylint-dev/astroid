class A:
    value = 123
class B:
    @property
    def value(self):
        return 456
A().value < B().value  # inferred: Const(True)
