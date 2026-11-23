# Regression test for https://github.com/pylint-dev/astroid/issues/264.
#
# Name resolution inside ``(k for k in dict(**k))`` used to bounce between
# the comprehension's ``k`` and the outer ``k`` until ``RecursionError``.
# The current behavior infers the generator's source as a dict instance
# without crashing.
def test(k):
    (k for k in __(dict(**k)))  # inferred: Instance(builtins.dict)
