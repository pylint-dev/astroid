from enum import Enum
Animal = Enum('Animal', 'ant bee cat dog')
for i in Animal.__members__:
    i  # inferred: Const('')
