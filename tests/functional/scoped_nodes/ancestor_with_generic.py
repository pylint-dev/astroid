from typing import TypeVar, Generic
T = TypeVar("T")
class A(Generic[T]):
    def a_method(self):
        print("hello")
# +2: inferred: ClassDef(ancestor_with_generic.B)
# +1: inferred.ancestors: ancestor_with_generic.A, typing.Generic, builtins.object
class B(A[T]): pass
# +2: inferred: ClassDef(ancestor_with_generic.C)
# +1: inferred.ancestors: ancestor_with_generic.B, ancestor_with_generic.A, typing.Generic, builtins.object
class C(B[str]): pass
