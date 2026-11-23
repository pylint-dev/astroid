# A type-annotated member of an Enum class where:
# - `member.value` is of type `nodes.Const` &
# - `member.value.value` is of type `str`
# is inferred as: `repr(member.value.value)`
from enum import Enum
class Veg(Enum):
    TOMATO: str = "sweet"

Veg.TOMATO.value  # inferred: Const('sweet')
