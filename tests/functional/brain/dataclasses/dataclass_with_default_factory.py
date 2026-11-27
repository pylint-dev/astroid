# Regression test for dataclasses with default values.
#
# Reported in https://github.com/pylint-dev/pylint/issues/7425
from dataclasses import dataclass
from typing import Union

@dataclass
class BadExampleParentClass:
    xyz: Union[str, int]

@dataclass
class BadExampleClass(BadExampleParentClass):
    xyz: str = ""

# +2: inferred: UnboundMethod(dataclass_with_default_factory.BadExampleClass.__init__)
# +1: inferred.args: self, xyz: str = ''
BadExampleClass.__init__

@dataclass
class GoodExampleParentClass:
    xyz: str

@dataclass
class GoodExampleClass(GoodExampleParentClass):
    xyz: str = ""

# +2: inferred: UnboundMethod(dataclass_with_default_factory.GoodExampleClass.__init__)
# +1: inferred.args: self, xyz: str = ''
GoodExampleClass.__init__
