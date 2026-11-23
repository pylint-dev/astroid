from enum import Enum
from typing import Optional

class A(Enum):  # inferred: ClassDef(no_crash_on_ann_assign_in_namedtuple.A)
    B: str = 'B'
