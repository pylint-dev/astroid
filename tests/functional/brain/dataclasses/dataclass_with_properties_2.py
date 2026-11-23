from dataclasses import dataclass

@dataclass
class Dataclass:
    other_attr: str
    attr: str

    @property
    def attr(self) -> str:
        return self.other_attr[-1]

    @attr.setter
    def attr(self, value: int) -> None:
        pass

# +2: inferred: UnboundMethod(dataclass_with_properties_2.Dataclass.__init__)
# +1: inferred.args: self, other_attr: str, attr: str = Uninferable
Dataclass.__init__
