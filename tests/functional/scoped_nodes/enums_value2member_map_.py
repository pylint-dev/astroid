# Check the `_value2member_map_` member is present in an Enum class.
from enum import Enum
class Veg(Enum):
    TOMATO: 1

# +2: inferred: ClassDef(enums_value2member_map_.Veg)
# +1: inferred.locals: TOMATO, __annotations__, __members__, __module__, __qualname__, _value2member_map_, name
Veg
