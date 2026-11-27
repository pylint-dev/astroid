x = [A] * 2
from collections import namedtuple
l = namedtuple('a', x)
l(1)  # inferred: Uninferable
