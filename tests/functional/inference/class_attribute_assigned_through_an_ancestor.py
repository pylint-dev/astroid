# A value bound on an ancestor does not leak into a class overriding it.
class Base:
    flag = None

    @classmethod
    def enable(cls):
        cls.flag = True

class Child(Base):
    flag = 0

Child.flag  # inferred: Const(0)
