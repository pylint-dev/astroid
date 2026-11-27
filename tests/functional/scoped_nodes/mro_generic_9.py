from dataclasses import dataclass
@dataclass
class A: ...
@dataclass
class B[T]: ...
@dataclass
class C[T](A, B[T]): ...  # mro: mro_generic_9.C, mro_generic_9.A, mro_generic_9.B, builtins.object
