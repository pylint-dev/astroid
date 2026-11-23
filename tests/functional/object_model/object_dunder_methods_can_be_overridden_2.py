class MyClass:
    def __eq__(self, other):
        return True

MyClass().__eq__  # inferred: BoundMethod(object_dunder_methods_can_be_overridden_2.MyClass.__eq__)
