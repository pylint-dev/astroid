from enum import Enum
Animal = Enum('Animal', 'ant bee cat dog')
# +2: inferred: Instance(__astroid_synthetic.Animal)
# +1: inferred.getattr(__iter__): FunctionDef(.EnumMeta.__iter__)
Animal
