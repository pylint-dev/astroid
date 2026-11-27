# ``from dataclasses import replace; replace(obj, ...)`` is handled.
from dataclasses import dataclass, replace

@dataclass
class Point:
    x: float
    y: float

p = Point(1.0, 2.0)
replace(p, x=3.0)  # inferred: Instance(replace_bare_name_form.Point)
