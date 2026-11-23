class A(object):
    pass
# +4: inferred: MroBoundMethod(builtins.type.mro)
# +3: inferred._proxied: FunctionDef(builtins.type.mro)
# +2: inferred.bound: ClassDef(builtins.type)
# +1: inferred.bound.name: 'type'
A.mro
# +4: inferred: SubclassesBoundMethod(builtins.type.__subclasses__)
# +3: inferred._proxied: FunctionDef(builtins.type.__subclasses__)
# +2: inferred.bound: ClassDef(builtins.type)
# +1: inferred.bound.name: 'type'
A.__subclasses__
