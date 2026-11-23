# Make sure partials are not automatically assigned.
from functools import partial
def test(a, b):
    return a + b
def scope():
    test2 = partial(test, 1)
    # +3: inferred: PartialFunction(PartialFunction)
    # +2: inferred.parent.scope(): FunctionDef(partial_does_not_affect_scope.scope)
    # +1: inferred.root(): Module(partial_does_not_affect_scope)
    test2
