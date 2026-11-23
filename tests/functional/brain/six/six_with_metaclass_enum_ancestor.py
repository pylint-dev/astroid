import six
from enum import Enum, EnumMeta

class FooMeta(EnumMeta):
    pass

class Foo(six.with_metaclass(FooMeta, Enum)):  # ancestors: enum.Enum, builtins.object
    bar = 1
