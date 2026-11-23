# Reported in https://github.com/pylint-dev/astroid/issues/3257 as a crash.
#
# Only simple-name annotations name a field; an attribute or subscript
# target such as ``a.b: str`` is not a field and has no ``name``.
from typing import NamedTuple
class C(NamedTuple):
    a.b: str
    basket[0]: str
    y: int
C  # inferred: ClassDef(__astroid_synthetic.C)  # inferred.instance_attrs: y
