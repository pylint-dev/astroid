import enum

class Mixin:
    pass

# +2: inferred: ClassDef(enum_multiple_base_classes.MyEnum)
# +1: inferred['one'].getattr(__class__)[0].is_subtype_of('.Mixin'): False
class MyEnum(Mixin, enum.Enum):
    one = 1
