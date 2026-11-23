import six

class C(object):
    pass
class B(C):
    pass
class A(six.with_metaclass(type, B)):  # mro: with_metaclass_mro.A, with_metaclass_mro.B, with_metaclass_mro.C, builtins.object
    pass
