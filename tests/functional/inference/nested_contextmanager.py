# Make sure contextmanager works with nested functions.
#
# Previously contextmanager would retrieve
# the first yield instead of the yield in the
# proper scope
#
# Fixes https://github.com/pylint-dev/pylint/issues/1746
from contextlib import contextmanager

@contextmanager
def outer():
    @contextmanager
    def inner():
        yield 2
    yield inner

with outer() as ctx:
    ctx  # inferred: FunctionDef(nested_contextmanager.outer.inner)
    with ctx() as val:
        val  # inferred: Const(2)
