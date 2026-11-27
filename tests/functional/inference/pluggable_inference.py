from collections import namedtuple
# +2: inferred: ClassDef(__astroid_synthetic.A)
# +1: inferred.instance_attrs: a, b
A = namedtuple('A', ['a', 'b'])
# +2: inferred: ClassDef(__astroid_synthetic.B)
# +1: inferred.instance_attrs: a, b
B = namedtuple('B', 'a b')
