# Overload stubs must not shadow the real dunder implementation.
#
# https://github.com/pylint-dev/astroid/issues/2448
from typing import overload

class Fraction:
    @overload
    def __truediv__(self, other: int) -> list: ...
    @overload
    def __truediv__(self, other: str) -> list: ...
    def __truediv__(self, other):
        return []

    @overload
    def __neg__(self) -> list: ...
    def __neg__(self):
        return []

Fraction() / 1  # inferred: List([])
-Fraction()  # inferred: List([])
