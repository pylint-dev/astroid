# Regression test for https://github.com/pylint-dev/astroid/issues/1683.
#
# When a method is redefined in the same class body, calling it on an
# instance must infer to the *last* definition. The bug caused inference to
# pick the first (no-return) definition, triggering false
# ``assignment-from-no-return`` in pylint.
class Test:
    def test(self):
        pass

    def test(self):
        return True

Test().test()  # inferred: Const(True)
