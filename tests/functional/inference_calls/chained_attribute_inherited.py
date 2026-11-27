# Tests for class methods that are inherited from a superclass.
#
# Based on https://github.com/pylint-dev/pylint/issues/4220.
class A:
    def f(self):
        return 42


class B(A):
    def __init__(self):
        self.a = A()
        result = self.a.f()

    def f(self):
        pass


B().a.f()  # inferred: Const(42)
