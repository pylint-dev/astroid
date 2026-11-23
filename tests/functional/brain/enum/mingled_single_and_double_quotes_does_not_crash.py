from enum import Enum
class A(Enum):
    a = 'x"y"'
A.a.value  # inferred: Const('x"y"')
