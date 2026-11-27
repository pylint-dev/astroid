# Test that unhashable builtin types have __hash__ = None.
# +2: inferred: ClassDef(builtins.list)
# +1: inferred.getattr(__hash__): BoundMethod(builtins.object.__hash__), BoundMethod(builtins.type.__hash__), Const(None), FunctionDef(builtins.object.__hash__)
list
