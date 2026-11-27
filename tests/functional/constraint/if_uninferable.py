# Test that when no inferred values satisfy all constraints, Uninferable is
# inferred.
def f1():
    x = None
    if x is not None:
        x  # inferred: Uninferable

def f2():
    x = 1
    if x is not None:
        pass
    else:
        x  # inferred: Uninferable
