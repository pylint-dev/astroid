from typing import NamedTuple

name = "X"
fields = [("a", int), ("b", str), ("c", bytes)]
NamedTuple(name, fields)  # inferred: Instance(typing.NamedTuple)
