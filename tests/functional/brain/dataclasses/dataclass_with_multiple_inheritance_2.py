from dataclasses import dataclass

@dataclass
class BaseParent:
    required: bool

@dataclass
class FirstChild(BaseParent):
    ...

@dataclass
class SecondChild(BaseParent):
    optional: bool = False

@dataclass
class GrandChild(FirstChild, SecondChild):
    ...

# +2: inferred: UnboundMethod(dataclass_with_multiple_inheritance_2.GrandChild.__init__)
# +1: inferred.args: self, required: bool, optional: bool = False
GrandChild.__init__
