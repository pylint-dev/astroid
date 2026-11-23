# Test method where the return value is based on an instance attribute with a
# constant value.
class A:
    def __init__(self):
        self.x = 1

    def get_x(self):
        return self.x

A().get_x()  # inferred: Const(1)
