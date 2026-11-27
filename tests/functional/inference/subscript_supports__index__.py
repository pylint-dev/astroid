class Index(object):
    def __index__(self): return 2
class LambdaIndex(object):
    __index__ = lambda self: self.foo
    @property
    def foo(self): return 1
class NonIndex(object):
    __index__ = lambda self: None
a = [1, 2, 3, 4]
a[Index()]  # inferred: Const(3)
a[LambdaIndex()]  # inferred: Const(2)
a[NonIndex()]  # inferred: InferenceError
