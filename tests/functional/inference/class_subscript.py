class Foo:
    def __class_getitem__(cls, *args, **kwargs):
        return cls

Foo[int]  # inferred: ClassDef(class_subscript.Foo)
