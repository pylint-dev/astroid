# A class whose mro cannot be computed falls back, it does not raise.
class Base:
    def eat(self):
        return "yum"

class Mixin:
    def eat(self):
        return super().eat()

class Broken(Mixin, Base, Mixin):
    pass

Broken().eat()  # inferred: Uninferable
