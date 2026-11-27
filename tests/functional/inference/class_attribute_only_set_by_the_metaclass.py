# The values of a metaclass attribute are kept when no class defines it.
class Meta(type):
    attr = 1
    attr = 2

class Klass(metaclass=Meta):
    pass

Klass.attr  # inferred: Const(1) | Const(2)
