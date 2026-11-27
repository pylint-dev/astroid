# dataclasses.replace(obj, ...) should infer to an instance of obj's class.
import dataclasses
from dataclasses import dataclass

@dataclass
class Point:
    x: float
    y: float

p = Point(1.0, 2.0)
dataclasses.replace(p, x=3.0)  # inferred: Instance(replace_returns_instance_of_caller_type.Point)
