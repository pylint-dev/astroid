# A functional Enum with a non-string class name is invalid.
from enum import Enum
Enum(1, "")  # inferred: Uninferable
