class Meta(type):
    def __or__(self, other):
        return 24
import six
class A(six.with_metaclass(Meta)):
    pass

A | A  # inferred: Const(24)
