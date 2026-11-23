from collections import namedtuple
class Invalid:
    def __str__(self):
        return 123  # will raise TypeError
Tuple = namedtuple("Tuple", [Invalid()])
Tuple  # inferred: Uninferable
