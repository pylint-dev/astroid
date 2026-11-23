from collections import namedtuple
Tuple = namedtuple("Tuple", "abc def", rename=True)
# +2: inferred: ClassDef(__astroid_synthetic.Tuple)
# +1: inferred.locals: _1, __annotations__, __module__, __qualname__, _asdict, _fields, _make, _replace, abc
Tuple
