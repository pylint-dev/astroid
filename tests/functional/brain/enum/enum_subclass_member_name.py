from enum import Enum

class EnumSubclass(Enum):
    pass

class Color(EnumSubclass):
    red = 1

Color.red.name  # inferred: Const('red')
