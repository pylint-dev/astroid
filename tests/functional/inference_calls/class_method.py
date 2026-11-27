# Tests for class method calls, both instance and with the class.
class A:
    @classmethod
    def method(cls, x):
        return x

A.method(42)  # inferred: Const(42)
A().method(42)  # inferred: Const(42)
