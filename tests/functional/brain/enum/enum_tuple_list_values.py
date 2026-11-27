import enum

class MyEnum(enum.Enum):
    a = (1, 2)
    b = [2, 4]
MyEnum.a.value  # inferred: Tuple((1, 2))
MyEnum.b.value  # inferred: List([2, 4])
