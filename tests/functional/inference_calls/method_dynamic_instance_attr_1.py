# Test method where the return value is based on an instance attribute with
# a dynamically-set value in a different method.
#
# In this case, the return value is Uninferable.
class A:
    def __init__(self, x):
        self.x = x

    def get_x(self):
        return self.x

A(1).get_x()  # inferred: Uninferable
