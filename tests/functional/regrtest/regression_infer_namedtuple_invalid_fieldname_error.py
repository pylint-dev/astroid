# Regression test for issue #2519.
from collections import namedtuple
namedtuple('a','}')  # inferred: Uninferable
