# Test that a truthiness guard on an instance whose ``__bool__`` reads guarded
# attributes of the same class does not recurse without end.
#
# Refs pylint-dev/pylint#11807
class Node:
    def __bool__(self):
        return not (self.left is None and self.right is None)

    def copy(self):
        if self:
            new = self.__class__()
            new.right = self.right.copy()

    def unlink(self):
        if self.left:
            pass
        elif self.right:
            node = self.right
            self.left, self.right = node.left, node.right
            self.right  # inferred: Uninferable
