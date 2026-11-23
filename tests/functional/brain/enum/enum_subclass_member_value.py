from enum import Enum

class EnumSubclass(Enum):
    pass

class Color(EnumSubclass):
    red = 1

Color.red.value  # inferred: Const(1)
