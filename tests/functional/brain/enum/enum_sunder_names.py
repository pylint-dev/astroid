# Test that both `_name_` and `_value_` sunder names exist
import enum


class MyEnum(enum.Enum):
    APPLE = 42
MyEnum.APPLE._name_  # inferred: Const('APPLE')
MyEnum.APPLE._value_  # inferred: Const(42)
