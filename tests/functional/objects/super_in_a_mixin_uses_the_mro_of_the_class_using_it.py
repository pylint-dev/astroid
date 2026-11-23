# A mixin has no base of its own to delegate to.
#
# ``Mixin.sound`` only has something to call because ``Leaf`` puts
# ``Base`` after ``Mixin`` in its mro.
class Base:
    def sound(self):
        return "moo"

class Mixin:
    def sound(self):
        return super().sound()

class Leaf(Mixin, Base):
    pass

Leaf().sound()  # inferred: Const('moo')  # inferred._proxied.name: 'str'
