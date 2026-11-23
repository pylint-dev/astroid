# Test that the `__annotations__` attribute is available in the class scope
class Test:
    __annotations__  # inferred: Uninferable
Test.__annotations__  # inferred: Uninferable
