# An annotation-only ``__slots__`` has no inferable value.
#
# Regression test for https://github.com/pylint-dev/astroid/issues/3067
class Klass:  # slots: None
    __slots__: None

    def method(self):
        self.attr = 1
