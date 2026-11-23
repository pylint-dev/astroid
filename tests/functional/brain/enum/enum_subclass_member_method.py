from enum import Enum

class EnumSubclass(Enum):
    def hello_pylint(self) -> str:
        return self.name

class Color(EnumSubclass):
    red = 1

Color.red.hello_pylint()  # inferred: Const('red')
