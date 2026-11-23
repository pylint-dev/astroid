import enum

# +2: inferred: ClassDef(int_enum.MyEnum)
# +1: inferred['one'].getattr(__class__)[0].is_subtype_of('builtins.int'): True
class MyEnum(enum.IntEnum):
    one = 1
