# A value bound on an ancestor does not leak through a shared scope.
class Base:
    pass

class Child(Base):
    pass

Base.attr = 1
Child.attr = "a"
Child.attr  # inferred: Const('a')
