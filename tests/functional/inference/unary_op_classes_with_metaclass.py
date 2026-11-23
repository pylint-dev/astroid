import six
class Meta(type):
    def __invert__(self):
        return 42
class A(six.with_metaclass(Meta)):
    pass
~A  # inferred: Const(42)
