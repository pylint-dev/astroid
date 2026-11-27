# Test that an instance of a class with an unknown base is never removed,
# since the base may define __call__.
import missing

class Unknown(missing.Base):
    pass

def f(x=Unknown()):
    if callable(x):
        x  # inferred: Instance(callable_unknown_base.Unknown) | Uninferable
    if not callable(x):
        x  # inferred: Instance(callable_unknown_base.Unknown) | Uninferable
