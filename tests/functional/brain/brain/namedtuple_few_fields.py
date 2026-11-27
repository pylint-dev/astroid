from typing import NamedTuple
NamedTuple("A", [("a",), ("b", str), ("c", bytes)])  # inferred: Instance(typing.NamedTuple)
