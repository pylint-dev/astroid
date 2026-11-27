# Tests for __init__ creation for dataclasses that use properties.
from dataclasses import dataclass

@dataclass
class Dataclass:
    attr: int

    @property
    def attr(self) -> int:
        return 1

    @attr.setter
    def attr(self, value: int) -> None:
        pass

class ParentOne(Dataclass):
    '''Docstring'''

@dataclass
class ParentTwo(Dataclass):
    '''Docstring'''

# +2: inferred: UnboundMethod(dataclass_with_properties_1.Dataclass.__init__)
# +1: inferred.args: self, attr: int = 1
Dataclass.__init__
# +2: inferred: UnboundMethod(dataclass_with_properties_1.Dataclass.__init__)
# +1: inferred.args: self, attr: int = 1
ParentOne.__init__
# +2: inferred: UnboundMethod(dataclass_with_properties_1.ParentTwo.__init__)
# +1: inferred.args: self, attr: int = 1
ParentTwo.__init__
