# Regression test for attr__new__ of ObjectModel.
#
# ObjectModel._instance is not always an bases.Instance, so we can't
# rely on the ._proxied attribute of an Instance.
# +1: getattr(__new__): BoundMethod(builtins.object.__new__)
class ClassHavingUnknownAncestors(Unknown):
    __slots__ = ["yo"]

    def test(self):
        self.not_yo = 42
