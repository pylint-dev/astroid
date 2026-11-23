class Enum:
    pass

class Color(Enum):
    red = 1

Color.red  # inferred: Const(1)
