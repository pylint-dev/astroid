from typing import NamedTuple

# +1: getattr(as_string): FunctionDef(namedtuple_can_correctly_access_methods.X.as_string)
class X(NamedTuple):
    a: int
    b: int
    def as_string(self):
        return '%s' % self.a
    def as_integer(self):
        return 2 + 3
X().as_integer()  # inferred: Const(5)
