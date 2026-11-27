from collections import namedtuple
Tuple = namedtuple("Tuple", field_names="a b c", rename=UNINFERABLE)
# +3: inferred: ClassDef(__astroid_synthetic.Tuple)
# +2: inferred.bases[0]: Name(tuple)
# +1: inferred.bases[0].name: 'tuple'
Tuple
