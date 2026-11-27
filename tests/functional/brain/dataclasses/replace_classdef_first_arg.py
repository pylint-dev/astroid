# Passing the class itself raises TypeError at runtime, so it is Uninferable.
import dataclasses
from dataclasses import dataclass

@dataclass
class Point:
    x: float = 0.0

dataclasses.replace(Point)  # inferred: Uninferable
