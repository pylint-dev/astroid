# Regression test for dataclasses with unknown base classes.
#
# Reported in https://github.com/pylint-dev/pylint/issues/7422
from dataclasses import dataclass, InitVar


@dataclass
class TestClass:
    '''Test Class'''

    config: InitVar = None

# +2: inferred: UnboundMethod(dataclass_with_unknown_typing.TestClass.__init__)
# +1: inferred.args: self, config=None
TestClass.__init__
