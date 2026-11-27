# Make sure decorators with the same names
# as a decorated method do not cause an infinite loop.
#
# See https://github.com/pylint-dev/astroid/issues/375
from functools import lru_cache

class Foo():
    @lru_cache()
    def lru_cache(self, value):
        print('Computing {}'.format(value))
        return value
Foo().lru_cache(1)  # inferred: Const(1)
