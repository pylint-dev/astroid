# Regression test for https://github.com/pylint-dev/astroid/issues/3200.
#
# A base dataclass can bind ``__init__`` to something that is not a function
# by annotating it as a field. Collecting the arguments of such a base should
# not crash with an AttributeError.
from dataclasses import dataclass

@dataclass
class A:
    __init__: int

@dataclass
class B(A):
    pass

# +2: inferred: UnboundMethod(dataclass_base_with_annotated_init_no_crash.B.__init__)
# +1: inferred.args: self
B.__init__
