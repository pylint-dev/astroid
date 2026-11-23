class Meta(type):
    def __getitem__(cls, arg):
        return 24
class A(object, metaclass=Meta):
    pass

A['Awesome']  # inferred: Const(24)
