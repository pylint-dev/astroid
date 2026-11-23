from enum import Enum
class TestEnum(Enum):
    def func(self):
        self.name  # inferred: Const('')
        self.value  # inferred: Uninferable
TestEnum.name  # inferred: Property(.name)
TestEnum.value  # inferred: Property(enum.Enum.value)
