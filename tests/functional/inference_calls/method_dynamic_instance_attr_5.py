# Test method where the return value is based on an instance attribute with
# a dynamically-set value in a different method, and is passed a constant value.
#
# But, where the outer and inner functions have the same signature.
#
# Inspired by https://github.com/pylint-dev/pylint/issues/400
#
# This is currently Uninferable.
class A:
    # Note: no initializer, so the only assignment happens in get_x

    def get_x(self, x):
        self.set_x(10)
        return self.x

    def set_x(self, x):
        self.x = x

A().get_x(1)  # inferred: Uninferable
