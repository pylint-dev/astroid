class First(object):
    def test(self): pass
class Second(First):
    def test2(self): pass
class Third(Second):
    test3 = 42
    def __init__(self):
        # +2: inferred: BoundMethod(super_getattr_single_inheritance.Second.test2)
        # +1: inferred.bound.name: 'Second'
        super(Third, self).test2
        # +2: inferred: BoundMethod(super_getattr_single_inheritance.First.test)
        # +1: inferred.bound.name: 'First'
        super(Third, self).test
        # test3 is local, no MRO lookup is done.
        super(Third, self).test3  # inferred: InferenceError
        # +3: inferred: Super
        # +2: inferred.getattr(test3): AttributeInferenceError
        # +1: inferred.igetattr(test3): AttributeInferenceError
        super(Third, self)

        # Unbounds.
        # +2: inferred: FunctionDef(super_getattr_single_inheritance.Second.test2)
        # +1: inferred.parent.name: 'Second'
        super(Third, Third).test2
        # +2: inferred: FunctionDef(super_getattr_single_inheritance.First.test)
        # +1: inferred.parent.name: 'First'
        super(Third, Third).test
