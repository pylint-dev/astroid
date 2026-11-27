# Test method where the return value is based on an instance attribute with
# a dynamically-set value in a different method, and is passed a constant value.
#
# This is currently Uninferable.
class A:
    # Note: no initializer, so the only assignment happens in get_x

    def get_x(self):
        self.set_x(10)
        return self.x

    def set_x(self, x):
        self.x = x

A().get_x()  # inferred: Uninferable
