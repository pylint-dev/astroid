# Regression test for https://github.com/pylint-dev/astroid/issues/2628.
#
# A dataclass inheriting from a class with duplicate bases in MRO
# (e.g., Protocol appearing both directly and indirectly) should not
# crash with DuplicateBasesError during AST transformation.
import dataclasses
from typing import TypeVar, Protocol

BaseT = TypeVar("BaseT")
T = TypeVar("T", bound=BaseT)

class ConfigBase(Protocol[BaseT]):
    ...

class Config(ConfigBase[T], Protocol[T]):
    ...

@dataclasses.dataclass
class DatasetConfig(Config[T]):
    name: str = "default"

# +1: inferred: UnboundMethod(dataclass_with_duplicate_bases_no_crash.DatasetConfig.__init__)
DatasetConfig.__init__
