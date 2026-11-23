# dataclasses.replace on a frozen dataclass returns an instance of the same type.
import dataclasses
from dataclasses import dataclass

@dataclass(frozen=True)
class FrozenPoint:
    x: float
    y: float

p = FrozenPoint(1.0, 2.0)
dataclasses.replace(p, x=3.0)  # inferred: Instance(replace_frozen_dataclass.FrozenPoint)
