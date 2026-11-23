# Check that a subclass of an int can still be inferred
#
# This test does not properly infer the value passed to the
# int subclass (5) but still returns a proper integer as we
# fake the result of the `len()` call.
class IntSubclass(int):
    pass

class F:
    def __len__(self):
        return IntSubclass(5)
len(F())  # inferred: Const(0)
