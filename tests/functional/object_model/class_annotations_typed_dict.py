# Test that we can access class annotations on various TypedDicts
from typing import TypedDict


class Apple(TypedDict):
    a: int
    b: str


Pear = TypedDict('OtherTypedDict', {'a': int, 'b': str})


Apple.__annotations__  # inferred: Uninferable
Pear.__annotations__  # inferred: Uninferable
