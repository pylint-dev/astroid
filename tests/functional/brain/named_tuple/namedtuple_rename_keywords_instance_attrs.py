# The instance carries the renamed field, not the name as written.
#
# https://github.com/pylint-dev/astroid/issues/242
from collections import namedtuple
Tuple = namedtuple("Tuple", "abc def", rename=True)
Tuple(1, 2)  # inferred: Instance(__astroid_synthetic.Tuple)  # inferred.instance_attrs: _1, abc
