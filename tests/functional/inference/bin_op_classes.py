class Meta(type):
    def __or__(self, other):
        return 24
class A(object, metaclass=Meta):
    pass

A | A  # inferred: Const(24)
