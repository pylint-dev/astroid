class Foo(object):
    @property
    def dict(self):
        return 42

class Bar(Foo):
    @property
    def dict(self):
        return super(Bar, self).dict

Bar().dict  # inferred: Const(42)
