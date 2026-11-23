# Test that we update the signature correctly based on the keyword.
from dataclasses import dataclass

@dataclass(kw_only=True)
class Foo:
    a: int
    e: str


@dataclass(kw_only=False)
class Bar(Foo):
    c: int


@dataclass(kw_only=False)
class Cee(Bar):
    d: int


@dataclass(kw_only=True)
class Dee(Cee):
    ee: int


# +2: inferred: UnboundMethod(kw_only_decorator.Foo.__init__)
# +1: inferred.args: self, *, a: int, e: str
Foo.__init__
# +2: inferred: UnboundMethod(kw_only_decorator.Bar.__init__)
# +1: inferred.args: self, c: int, *, a: int, e: str
Bar.__init__
# +2: inferred: UnboundMethod(kw_only_decorator.Cee.__init__)
# +1: inferred.args: self, c: int, d: int, *, a: int, e: str
Cee.__init__
# +2: inferred: UnboundMethod(kw_only_decorator.Dee.__init__)
# +1: inferred.args: self, c: int, d: int, *, a: int, e: str, ee: int
Dee.__init__
