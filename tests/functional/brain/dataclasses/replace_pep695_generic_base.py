# dataclasses.replace propagates the concrete subclass for PEP 695 generics.
import dataclasses
from dataclasses import dataclass
from typing import ClassVar, Self
from abc import ABC

class Base[T](ABC):
    __dataclass_fields__: ClassVar
    def rebuild(self, items) -> Self:
        return dataclasses.replace(self, **{"items": items})

@dataclass
class Child(Base):
    items: tuple = ()

c = Child()
c.rebuild(())  # inferred: Instance(replace_pep695_generic_base.Child)
