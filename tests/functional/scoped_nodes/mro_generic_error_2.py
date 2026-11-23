from typing import Generic, TypeVar
T = TypeVar('T')
class A(Generic[T]): ...
class B(A[T], A[T]): ...  # mro: DuplicateBasesError
