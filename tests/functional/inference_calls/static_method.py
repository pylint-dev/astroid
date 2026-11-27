# Tests for static method calls, both instance and with the class.
class A:
    @staticmethod
    def method(x):
        return x

A.method(42)  # inferred: Const(42)
A().method(42)  # inferred: Const(42)
