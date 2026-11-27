# Test that builtins alias, such as typing.List, are subscriptable
import typing
# +2: inferred: ClassDef(typing.List)
# +1: inferred.getattr(__iter__): FunctionDef(builtins.list.__iter__)
typing.List[int]
