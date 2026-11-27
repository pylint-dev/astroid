# Regression test for https://github.com/pylint-dev/pylint/issues/5244
# See also https://github.com/pylint-dev/astroid/pull/1234
#
# This test should succeed without any error.
class A:
    def __len__(self) -> int:
        return 42

class Crash:
    def __len__(self) -> int:
        a = A()
        return len(a)

len(Crash())  # inferred: Const(42)
