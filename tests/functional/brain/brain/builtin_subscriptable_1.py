# Starting with python3.9 builtin types such as list are subscriptable.
# Any builtin class such as "enumerate" or "staticmethod" also works.
# +2: inferred: ClassDef(builtins.tuple)
# +1: inferred.getattr(__iter__): FunctionDef(builtins.tuple.__iter__)
tuple[int]
