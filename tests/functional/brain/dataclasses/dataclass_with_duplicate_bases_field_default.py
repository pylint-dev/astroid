# Regression test for _get_previous_field_default with broken MRO.
#
# When a parent dataclass defines a field with a default and a child (with
# duplicate bases in its MRO) re-annotates that field without a value,
# _get_previous_field_default should not crash with DuplicateBasesError.
#
# See https://github.com/pylint-dev/astroid/issues/2628.
import dataclasses
from typing import TypeVar, Protocol

BaseT = TypeVar("BaseT")
T = TypeVar("T", bound=BaseT)

class ConfigBase(Protocol[BaseT]):
    ...

class Config(ConfigBase[T], Protocol[T]):
    ...

@dataclasses.dataclass
class BaseConfig(Config[T]):
    name: str = "default"

@dataclasses.dataclass
class ChildConfig(BaseConfig[T]):
    name: str

# +1: inferred: UnboundMethod(dataclass_with_duplicate_bases_field_default.ChildConfig.__init__)
ChildConfig.__init__
