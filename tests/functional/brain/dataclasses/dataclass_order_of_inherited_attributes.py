# Test that an attribute in a child does not get put at the end of the init.
from dataclass import dataclass


@dataclass
class Parent:
    a: str
    b: str


@dataclass
class Child(Parent):
    c: str
    a: str


@dataclass(kw_only=True)
class KeywordOnlyParent:
    a: int
    b: str


@dataclass
class NormalChild(KeywordOnlyParent):
    c: str
    a: str


@dataclass(kw_only=True)
class KeywordOnlyChild(KeywordOnlyParent):
    c: str
    a: str


# +2: inferred: UnboundMethod(dataclass_order_of_inherited_attributes.Child.__init__)
# +1: inferred.args: self, a: str, b: str, c: str
Child.__init__
# +2: inferred: UnboundMethod(dataclass_order_of_inherited_attributes.NormalChild.__init__)
# +1: inferred.args: self, a, c: str, *, b: str
NormalChild.__init__
# +2: inferred: UnboundMethod(dataclass_order_of_inherited_attributes.KeywordOnlyChild.__init__)
# +1: inferred.args: self, *, a: str, b: str, c: str
KeywordOnlyChild.__init__
