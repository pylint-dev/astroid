# Test typing.Generic is subscriptable with __class_getitem__ (added in PY37)
from typing import Generic, TypeVar
T = TypeVar('T')
# +2: inferred: ClassDef(typing.Generic)
# +1: inferred.getattr(__class_getitem__): FunctionDef(.__class_getitem__)
Generic[T]
