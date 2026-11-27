# Test that MutableSet is subscriptable
import typing
# +3: inferred: ClassDef(typing.MutableSet)
# +2: inferred.mro: typing.MutableSet, _collections_abc.MutableSet, _collections_abc.Set, _collections_abc.Collection, _collections_abc.Sized, _collections_abc.Iterable, _collections_abc.Container, builtins.object
# +1: inferred.getattr(__class_getitem__): FunctionDef(.__class_getitem__), FunctionDef(.__class_getitem__), FunctionDef(.__class_getitem__), FunctionDef(.__class_getitem__), FunctionDef(.__class_getitem__), FunctionDef(.__class_getitem__)
typing.MutableSet[int]
