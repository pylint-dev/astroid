# A functional Enum whose field names are bytes is invalid.
#
# Regression test for https://github.com/pylint-dev/astroid/issues/3189
from enum import Enum
Enum("", b"")  # inferred: Uninferable
