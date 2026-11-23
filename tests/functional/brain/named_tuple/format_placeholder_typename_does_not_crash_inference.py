# A typename containing str.format placeholders must not be formatted.
#
# Reported in https://github.com/pylint-dev/astroid/issues/3199.
from collections import namedtuple
Tuple = namedtuple("{0}", "")
Tuple  # inferred: Uninferable
