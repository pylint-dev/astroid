class Base:
    def __call__(self, value):
        return self.factor * value

class Callable(Base):
    factor = 2

class Holder:
    target = Callable()

Holder().target(42)  # inferred: Const(84)
