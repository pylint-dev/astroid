type Alias = str
# +4: <3.14: inferred: Instance(typing.TypeAliasType)
# +3: >=3.14: inferred: Instance(typing.TypeAliasType)
# +2: <3.14: inferred.getattr(evaluate_value): AttributeInferenceError
# +1: >=3.14: inferred.getattr(evaluate_value): FunctionDef(typing.TypeAliasType.evaluate_value)
Alias
