from typing import Generic, TypeVar
T1 = TypeVar('T1')
T2 = TypeVar('T2')
class A(Generic[T1], Generic[T2]): ...  # mro: DuplicateBasesError
