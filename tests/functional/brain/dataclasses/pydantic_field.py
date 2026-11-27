# Test that pydantic.Field attributes are currently Uninferable.
#
# (Eventually, we can extend the brain to support pydantic.Field)
from pydantic import Field
from pydantic.dataclasses import dataclass

@dataclass
class A:
    name: str = Field("hi")

A.name  # inferred: Uninferable
A().name  # inferred: Instance(builtins.str) | Uninferable
