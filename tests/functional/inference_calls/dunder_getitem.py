# Test for the special method __getitem__ (used by Instance.getitem).
#
# This is currently Uninferable, until we can infer instance attribute values through
# constructor calls.
class A:
    def __init__(self, x):
        self.x = x

    def __getitem__(self, i):
        return self.x + i

A(1)[2]  # inferred: Uninferable
