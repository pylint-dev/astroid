class Foo(object):
    pass
class Bar(object):
    pass
isinstance(Bar(), Foo)  # inferred: Const(False)
