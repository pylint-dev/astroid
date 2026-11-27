from collections import namedtuple
Tuple = namedtuple("{message.foo}", "")
Tuple  # inferred: Uninferable
