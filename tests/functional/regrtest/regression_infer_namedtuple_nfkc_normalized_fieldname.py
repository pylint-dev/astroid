# Regression test for pylint-dev/pylint#8746.
#
# ``namedtuple`` accepts any identifier as a field name, but the parser stores
# identifiers in their NFKC-normalized form, so a field written as "µ"
# (MICRO SIGN) ends up under "μ" (GREEK SMALL LETTER MU).
from collections import namedtuple
# +2: inferred: ClassDef(__astroid_synthetic.mu)
# +1: inferred.locals: __annotations__, __module__, __qualname__, _asdict, _fields, _make, _replace, μ
namedtuple('mu', ['µ'])
