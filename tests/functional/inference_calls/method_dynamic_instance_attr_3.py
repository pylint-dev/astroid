# Test method where the return value is based on an instance attribute with
# a dynamically-set value in a different method.
#
# This is currently Uninferable.
class A:
    def get_x(self, x):  # x is unused
        return self.x

    def set_x(self, x):
        self.x = x

A().get_x(10)  # inferred: Uninferable
