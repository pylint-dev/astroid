from collections import namedtuple
SomeClass = namedtuple('SomeClass', ['name'])
items = [SomeClass(name='some name')]

some_str = ''
# +1: inferred: Instance(__astroid_synthetic.SomeClass)
some_str += ', '.join(__(item) for item in items)
