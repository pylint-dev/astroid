# Test that random.sample does not crash when an element is not a source node.
#
# Regression test for https://github.com/pylint-dev/astroid/issues/3310
from random import sample
# +1: inferred: List(Instance(builtins.list))
sample(list({list(None)}) * 1, 1)
