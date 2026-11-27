# typing.Annotated is subscriptable with __class_getitem__ below 3.13.
import typing
# +4: <3.13: inferred: ClassDef(typing.Annotated)
# +3: >=3.13: inferred: FunctionDef(typing.Annotated)
# +2: <3.13: inferred.getattr(__class_getitem__): FunctionDef(.__class_getitem__)
# +1: >=3.13: inferred.getattr(__class_getitem__): AttributeInferenceError
typing.Annotated[str, "data"]
