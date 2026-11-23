# Test method where the return value is based on an instance attribute with
# a dynamically-set value in the same method.
class A:
    # Note: no initializer, so the only assignment happens in get_x

    def get_x(self, x):
        self.x = x
        return self.x

A().get_x(1)  # inferred: Const(1)
