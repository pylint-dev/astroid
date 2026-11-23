class Foo(object):
    pass
class Bar(object):
    pass
issubclass(Bar, Foo)  # inferred: Const(False)
