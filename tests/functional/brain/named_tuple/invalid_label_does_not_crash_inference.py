import collections
a = collections.namedtuple( 'a', ['b c'] )
# +2: inferred: ClassDef(__astroid_synthetic.a)
# +1: inferred.locals: __annotations__, __module__, __qualname__, _asdict, _fields, _make, _replace
a
