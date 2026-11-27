# Test that comprehension conditions constrain names from outer scopes
# used in the element expression.
def f(y = None):
    return [y for x in [1, 2] if y is not None]  # value.elt.inferred: Uninferable
