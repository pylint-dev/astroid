# Duplicate fields are renamed rather than collapsed on the instance.
#
# https://github.com/pylint-dev/astroid/issues/242
from collections import namedtuple
Tuple = namedtuple("Tuple", "abc abc abc", rename=True)
# +2: inferred: Instance(__astroid_synthetic.Tuple)
# +1: inferred.instance_attrs: _1, _2, abc
Tuple(1, 2, 3)
