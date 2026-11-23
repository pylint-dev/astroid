# dataclasses.replace propagates the concrete subclass type, not the base.
import dataclasses
from dataclasses import dataclass
from typing import ClassVar, Generic, TypeVar
try:
    from typing import Self
except ImportError:
    from typing_extensions import Self
from abc import ABC

_T = TypeVar("_T", covariant=True)

class Base(Generic[_T], ABC):
    __dataclass_fields__: ClassVar
    def rebuild(self, items) -> Self:
        return dataclasses.replace(self, **{"items": items})

@dataclass
class Child(Base[_T]):
    items: tuple = ()

c = Child()
c.rebuild(())  # inferred: Instance(replace_returns_subclass_instance.Child)
