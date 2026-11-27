# Test that the type aliased thanks to typing._alias function are
# correctly inferred.
# typing_alias function is introduced with python37.
# OrderedDict in the typing module appears only with python 3.7.2
import typing
# +2: inferred: ClassDef(typing_alias_type_2.Derived2)
# +1: inferred.mro: typing_alias_type_2.Derived2, typing.OrderedDict, collections.OrderedDict, builtins.dict, builtins.object
class Derived2(typing.OrderedDict[int, str]):
    pass
