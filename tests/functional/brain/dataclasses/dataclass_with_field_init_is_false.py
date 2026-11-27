# When init=False it shouldn't end up in the __init__.
from dataclasses import dataclass, field


@dataclass
class First:
    a: int

@dataclass
class Second(First):
    a: int = field(init=False, default=1)

@dataclass
class SecondChild(Second):
    a: float

@dataclass
class ThirdChild(SecondChild):
    a: str

@dataclass
class Third(First):
    a: str

# +2: inferred: UnboundMethod(dataclass_with_field_init_is_false.First.__init__)
# +1: inferred.args: self, a: int
First.__init__
# +2: inferred: UnboundMethod(dataclass_with_field_init_is_false.Second.__init__)
# +1: inferred.args: self
Second.__init__
# +2: inferred: UnboundMethod(dataclass_with_field_init_is_false.SecondChild.__init__)
# +1: inferred.args: self, a: float = 1
SecondChild.__init__
# +2: inferred: UnboundMethod(dataclass_with_field_init_is_false.ThirdChild.__init__)
# +1: inferred.args: self, a: str = 1
ThirdChild.__init__
# +2: inferred: UnboundMethod(dataclass_with_field_init_is_false.Third.__init__)
# +1: inferred.args: self, a: str
Third.__init__
