# Regression test for dataclasses with multiple inheritance.
#
# Reported in https://github.com/pylint-dev/pylint/issues/7427
# Reported in https://github.com/pylint-dev/pylint/issues/7434
from dataclasses import dataclass

@dataclass
class BaseParent:
    _abc: int = 1

@dataclass
class AnotherParent:
    ef: int = 2

@dataclass
class FirstChild(BaseParent, AnotherParent):
    ghi: int = 3

@dataclass
class ConvolutedParent(AnotherParent):
    '''Convoluted Parent'''

@dataclass
class SecondChild(BaseParent, ConvolutedParent):
    jkl: int = 4

@dataclass
class OverwritingParent:
    ef: str = "2"

@dataclass
class OverwrittenChild(OverwritingParent, AnotherParent):
    '''Overwritten Child'''

@dataclass
class OverwritingChild(BaseParent, AnotherParent):
    _abc: float = 1.0
    ef: float = 2.0

class NotADataclassParent:
    ef: int = 2

@dataclass
class ChildWithMixedParents(BaseParent, NotADataclassParent):
    ghi: int = 3

# +2: inferred: UnboundMethod(dataclass_with_multiple_inheritance_1.FirstChild.__init__)
# +1: inferred.args: self, ef: int = 2, _abc: int = 1, ghi: int = 3
FirstChild.__init__
# +2: inferred: UnboundMethod(dataclass_with_multiple_inheritance_1.SecondChild.__init__)
# +1: inferred.args: self, ef: int = 2, _abc: int = 1, jkl: int = 4
SecondChild.__init__
# +2: inferred: UnboundMethod(dataclass_with_multiple_inheritance_1.OverwrittenChild.__init__)
# +1: inferred.args: self, ef: str = '2'
OverwrittenChild.__init__
# +2: inferred: UnboundMethod(dataclass_with_multiple_inheritance_1.OverwritingChild.__init__)
# +1: inferred.args: self, ef: float = 2.0, _abc: float = 1.0
OverwritingChild.__init__
# +2: inferred: UnboundMethod(dataclass_with_multiple_inheritance_1.ChildWithMixedParents.__init__)
# +1: inferred.args: self, _abc: int = 1, ghi: int = 3
ChildWithMixedParents.__init__
