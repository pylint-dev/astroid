# Test that random.sample does not crash when elements are Uninferable.
#
# Regression test for https://github.com/pylint-dev/astroid/issues/2518
import random
random.sample(1*[b], 1)  # inferred: List([None]) | Uninferable
