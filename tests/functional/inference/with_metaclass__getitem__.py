class Meta(type):
    def __getitem__(cls, arg):
        return 24
import six
class A(six.with_metaclass(Meta)):
    pass

A['Awesome']  # inferred: Const(24)
