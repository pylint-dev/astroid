# Test slots for Generic subclass.
from typing import Generic, TypeVar
T = TypeVar('T')
class A(Generic[T]):  # inferred: ClassDef(typing_generic_slots.A)  # inferred.slots: value
    __slots__ = ['value']
    def __init__(self, value):
        self.value = value
