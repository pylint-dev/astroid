# +5: type_params[0]: TypeVar(T: int = int)
# +4: type_params[0].bound: Name(int)
# +3: type_params[0].bound.name: 'int'
# +2: type_params[0].default_value: Name(int)
# +1: type_params[0].default_value.name: 'int'
type Point[T: int = int] = T
