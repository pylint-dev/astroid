from enum import Enum
f = Enum('Audience', ['a', 'b', 'c'])
f  # inferred: Instance(__astroid_synthetic.Audience)
# +3: inferred: Instance(.EnumMeta.__call__.EnumAttribute)
# +2: inferred.igetattr(name): Const('')
# +1: inferred.igetattr(value): Const(0)
f(1)
