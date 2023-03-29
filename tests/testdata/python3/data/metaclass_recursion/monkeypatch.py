# https://github.com/pylint-dev/astroid/issues/749
# Not an actual module but allows us to reproduce the issue
from tests.testdata.python3.data.metaclass_recursion import parent

class MonkeyPatchClass(parent.OriginalClass):
    _original_class = parent.OriginalClass

    @classmethod
    def patch(cls):
        if parent.OriginalClass != MonkeyPatchClass:
            cls._original_class = parent.OriginalClass
            parent.OriginalClass = MonkeyPatchClass

    @classmethod
    def unpatch(cls):
        if parent.OriginalClass == MonkeyPatchClass:
            parent.OriginalClass = cls._original_class
