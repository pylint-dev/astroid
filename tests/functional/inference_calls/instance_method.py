# Tests for instance method, both bound and unbound.
class A:
    def method(self, x):
        return x

A().method(42)  # inferred: Const(42)

# In this case, the 1 argument is bound to self, which is ignored in the method
A.method(1, 42)  # inferred: Const(42)
