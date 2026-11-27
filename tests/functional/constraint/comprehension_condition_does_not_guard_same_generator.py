# Test that a generator's conditions don't constrain its own target, iterable
# or the element of a preceding generator.
def f(y = None):
    # +1: value.generators[0].iter.elts[0].inferred: Const(None) | Uninferable
    return [x for x in [y] if y is not None]
