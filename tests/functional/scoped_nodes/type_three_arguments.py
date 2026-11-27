# +7: inferred: ClassDef(type_three_arguments.A)
# +6: inferred.basenames: ['object']
# +5: inferred.getattr(missing): AttributeInferenceError
# +4: inferred['a']: Const(1)
# +3: inferred['a'].value: 1
# +2: inferred['b']: Const(2)
# +1: inferred['b'].value: 2
type('A', (object, ), {"a": 1, "b": 2, missing: 3})
