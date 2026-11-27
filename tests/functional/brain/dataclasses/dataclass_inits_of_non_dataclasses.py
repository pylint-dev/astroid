# Regression test for __init__ mangling for non dataclasses.
#
# Regression test against changes tested in test_dataclass_with_multiple_inheritance
from dataclasses import dataclass

@dataclass
class DataclassParent:
    _abc: int = 1


class NotADataclassParent:
    ef: int = 2


class FirstChild(DataclassParent, NotADataclassParent):
    ghi: int = 3


class SecondChild(DataclassParent, NotADataclassParent):
    ghi: int = 3

    def __init__(self, ef: int = 3):
        self.ef = ef


class ThirdChild(NotADataclassParent, DataclassParent):
    ghi: int = 3

    def __init__(self, ef: int = 3):
        self.ef = ef

# +2: inferred: UnboundMethod(dataclass_inits_of_non_dataclasses.DataclassParent.__init__)
# +1: inferred.args: self, _abc: int = 1
FirstChild.__init__
# +2: inferred: UnboundMethod(dataclass_inits_of_non_dataclasses.SecondChild.__init__)
# +1: inferred.args: self, ef: int = 3
SecondChild.__init__
# +2: inferred: UnboundMethod(dataclass_inits_of_non_dataclasses.ThirdChild.__init__)
# +1: inferred.args: self, ef: int = 3
ThirdChild.__init__
