from enum import Enum
Animal = Enum('Animal', 'ant bee cat dog')
Animal['ant']  # inferred: Instance(.EnumMeta.__getitem__.Value)
Animal['ant'].name  # inferred: Const('')
