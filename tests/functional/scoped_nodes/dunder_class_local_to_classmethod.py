class MyClass:
    @classmethod
    def test(cls):
        __class__  # inferred: ClassDef(dunder_class_local_to_classmethod.MyClass)
