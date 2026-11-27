# A functional Enum member given as an empty tuple is invalid.
#
# Reading the member name via ``const.elts[0]`` used to raise an
# uncaught ``IndexError``.
from enum import Enum
Enum("E", [()])  # inferred: Uninferable
