# Test that the type aliased thanks to typing._alias function are
# correctly inferred.
# typing_alias function is introduced with python37
from typing import TypeVar, MutableSet

T = TypeVar("T")
MutableSet[T]

# +2: inferred: ClassDef(typing_alias_type.Derived1)
# +1: inferred.mro: typing_alias_type.Derived1, typing.MutableSet, _collections_abc.MutableSet, _collections_abc.Set, _collections_abc.Collection, _collections_abc.Sized, _collections_abc.Iterable, _collections_abc.Container, builtins.object
class Derived1(MutableSet[T]):
    pass
