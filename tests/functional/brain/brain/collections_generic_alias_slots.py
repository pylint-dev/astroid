# Test slots for a class which is a subclass of a generic alias type.
import collections
import typing
Type = typing.TypeVar('Type')
# +2: inferred: ClassDef(collections_generic_alias_slots.A)
# +1: inferred.slots: _value
class A(collections.abc.AsyncIterator[Type]):
    __slots__ = ('_value',)
    def __init__(self, value: collections.abc.AsyncIterator[Type]):
        self._value = value
