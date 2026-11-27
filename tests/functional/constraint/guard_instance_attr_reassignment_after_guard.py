# Test that an instance attribute assigned between a guard and the use is not
# constrained.
class A:
    def __init__(self, x = 1):
        self.x = x

    def method(self):
        if self.x is None:
            return
        self.x = None
        self.x  # inferred: Const(1) | Const(None) | Uninferable
