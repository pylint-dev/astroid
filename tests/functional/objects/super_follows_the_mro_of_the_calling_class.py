# ``super()`` in ``Left`` reaches ``Right``, which is not an ancestor of it.
#
# ``Right`` comes after ``Left`` and before ``Base`` in ``Leaf``'s mro, so
# that is what ``Left.pick`` delegates to when called on a ``Leaf``.
class Base:
    def pick(self):
        return "apple"

class Left(Base):
    def pick(self):
        return super().pick()

class Right(Base):
    def pick(self):
        return "banana"

class Leaf(Left, Right):
    pass

Leaf().pick()  # inferred: Const('apple') | Const('banana')
