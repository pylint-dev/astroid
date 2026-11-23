# Check that a type (str for example) that inherits
# from type does not have __class_getitem__ method even
# when it is used as a subscript
# +2: annotation.value.inferred: ClassDef(builtins.str)
# +1: annotation.value.inferred.getattr(__class_getitem__)[0]: AttributeInferenceError
a: str[int] = "abc"
