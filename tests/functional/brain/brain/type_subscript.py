# Check that type object has the __class_getitem__ method
# when it is used as a subscript
# +2: annotation.value.inferred: ClassDef(.type)
# +1: annotation.value.inferred.getattr(__class_getitem__)[0]: FunctionDef(.type.__class_getitem__)
a: type[int] = int
