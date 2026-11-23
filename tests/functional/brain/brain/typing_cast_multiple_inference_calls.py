# Inference of an outer function should not store the result for cast.
from typing import TypeVar, cast
T = TypeVar("T")
def ident(var: T) -> T:
    return cast(T, var)

ident(2)  # inferred: Const(2)
ident("Hello")  # inferred: Const('Hello')
