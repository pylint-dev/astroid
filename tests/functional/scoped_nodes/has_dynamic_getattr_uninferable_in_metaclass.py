# An uninferable ``__getattr__`` found in the metaclass is not dynamic.
#
# The result used to be ``Uninferable`` instead of a bool.
class Meta(type):
    __getattr__ = undefined_name

class A(metaclass=Meta):  # has_dynamic_getattr(): False
    pass
