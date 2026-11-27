from typing import Generic, TypeVar
T = TypeVar("T")
class Container(Generic[T]): ...
type Alias = str
Container[Alias]()  # inferred: Instance(instantiate_class_subscripted_with_type_alias.Container)
