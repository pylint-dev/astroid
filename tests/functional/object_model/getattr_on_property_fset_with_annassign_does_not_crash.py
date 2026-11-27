# Test that getattr on property fset doesn't crash with AnnAssign.
from typing import TypeVar, Generic

T = TypeVar('T')

class Base:
    _x: object
    @property
    def x(self):
        return self._x
    @x.setter
    def x(self, val):
        self._x = val

class Child(Base, Generic[T]):
    _x: T
    @property
    def x(self) -> T:
        return self._x
    @x.setter
    def x(self, val):
        # +1: inferred: PropertyFuncAccessor(getattr_on_property_fset_with_annassign_does_not_crash.Base.x.fset)
        getattr(Base.x, "fset", None)
