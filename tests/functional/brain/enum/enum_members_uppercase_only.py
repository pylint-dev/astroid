# Originally reported in https://github.com/pylint-dev/pylint/issues/7402.
# ``nodes.AnnAssign`` nodes with no assigned values do not appear inside ``__members__``.
#
# Test that only enum members `MARS` and `radius` appear in the `__members__` container while
# the attribute `mass` does not.
from enum import Enum
# +3: igetattr(__members__).items: [[Const('MARS'), Name(MARS)], [Const('radius'), Name(radius)]]
# +2: igetattr(__members__).items[0][1].name: 'MARS'
# +1: igetattr(__members__).items[1][1].name: 'radius'
class Planet(Enum):
    MARS = (1, 2)
    radius: int = 1
    mass: int

    def __init__(self, mass, radius):
        self.mass = mass
        self.radius = radius

Planet.MARS.value
