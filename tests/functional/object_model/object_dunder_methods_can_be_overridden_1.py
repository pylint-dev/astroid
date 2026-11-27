# Test that ObjectModel dunders don't block class overrides.
class MyClass:
    def __eq__(self, other):
        return "custom equality"

MyClass().__eq__(None)  # inferred: Const('custom equality')
