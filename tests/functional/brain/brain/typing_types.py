from typing import TypeVar, Iterable, Tuple, NewType, Dict, Union
TypeVar('MyTypeVar', int, float, complex)  # inferred: ClassDef(.MyTypeVar)
Iterable[Tuple[MyTypeVar, MyTypeVar]]  # inferred: ClassDef(typing.Iterable)
TypeVar('AnyStr', str, bytes)  # inferred: ClassDef(.AnyStr)
NewType('UserId', str)  # inferred: ClassDef(.UserId)
Dict[str, str]  # inferred: ClassDef(typing.Dict)
Union[int, str]  # inferred: ClassDef(.Union)
