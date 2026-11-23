from collections import namedtuple
Tuple = namedtuple(typename="Tuple", field_names="a b c", rename=UNINFERABLE)
# +2: inferred: ClassDef(__astroid_synthetic.Tuple)
# +1: inferred.locals: __annotations__, __module__, __qualname__, _asdict, _fields, _make, _replace, a, b, c
Tuple
