class Meta(type):
    def __invert__(self):
        return 42
class A(object, metaclass=Meta):
    pass
~A  # inferred: Const(42)
