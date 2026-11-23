# A parent field() without a default gives no default to the child.
from dataclasses import dataclass, field

@dataclass
class Parent:
    a: int = field(init=False)

@dataclass
class Child(Parent):
    a: int

# +2: inferred: UnboundMethod(dataclass_with_field_init_is_false_without_default.Child.__init__)
# +1: inferred.args: self, a: int
Child.__init__
