# Test that keyword only fields get correctly put at the end of the __init__.
from dataclasses import dataclass, field

@dataclass
class Parent:
    p1: int = field(kw_only=True, default=0)

@dataclass
class Child(Parent):
    c1: str

@dataclass(kw_only=True)
class GrandChild(Child):
    p2: int = field(kw_only=False, default=1)
    p3: int = field(kw_only=True, default=2)

# +2: inferred: UnboundMethod(kw_only_in_field_call.Parent.__init__)
# +1: inferred.args: self, *, p1: int = 0
Parent.__init__
# +2: inferred: UnboundMethod(kw_only_in_field_call.Child.__init__)
# +1: inferred.args: self, c1: str, *, p1: int = 0
Child.__init__
# +2: inferred: UnboundMethod(kw_only_in_field_call.GrandChild.__init__)
# +1: inferred.args: self, c1: str, p2: int = 1, *, p1: int = 0, p3: int = 2
GrandChild.__init__
