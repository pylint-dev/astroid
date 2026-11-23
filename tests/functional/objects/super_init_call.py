# Test that __init__ is still callable.
class SuperUsingClass:
    @staticmethod
    def test():
        super(object, 1).__new__  # inferred: BoundMethod(builtins.object.__new__)
        super(object, 1).__init__  # inferred: BoundMethod(builtins.object.__init__)
class A:
    pass
A().__new__  # inferred: BoundMethod(builtins.object.__new__)
A().__init__  # inferred: BoundMethod(builtins.object.__init__)
