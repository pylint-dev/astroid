# A functional Enum with a non-string member name is invalid.
#
# Regression test for https://github.com/pylint-dev/astroid/issues/3068
from enum import Enum
Enum("e", (1,))  # inferred: Uninferable
