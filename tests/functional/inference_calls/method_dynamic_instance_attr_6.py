# Test method where the return value is based on an instance attribute with
# a dynamically-set value in a different method, and is passed a dynamic value.
#
# This is currently Uninferable.
class A:
    # Note: no initializer, so the only assignment happens in get_x

    def get_x(self, x):
        self.set_x(x + 1)
        return self.x

    def set_x(self, x):
        self.x = x

A().get_x(1)  # inferred: Uninferable
