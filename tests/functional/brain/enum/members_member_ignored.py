from enum import Enum
class Animal(Enum):
    a = 1
    __members__ = {}
# +2: inferred: Dict(Const('a'): Name(a), Const('__members__'): Name(__members__))
# +1: inferred.locals.__contains__('keys'): True
Animal.__members__
