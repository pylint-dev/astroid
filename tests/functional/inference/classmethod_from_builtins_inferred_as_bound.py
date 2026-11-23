import builtins

class Foo():
    @classmethod
    def bar1(cls, text):
        pass

    @builtins.classmethod
    def bar2(cls, text):
        pass

Foo.bar1  # inferred: BoundMethod(classmethod_from_builtins_inferred_as_bound.Foo.bar1)
Foo.bar2  # inferred: BoundMethod(classmethod_from_builtins_inferred_as_bound.Foo.bar2)
