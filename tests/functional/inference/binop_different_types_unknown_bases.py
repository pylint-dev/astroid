from foo import bar

class A(bar):
    pass
class B(object):
    def __radd__(self, other):
        return other
A() + B()  # inferred: Uninferable
