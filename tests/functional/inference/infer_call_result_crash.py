class A(object):
    def __mul__(self, other):
        return type.__new__()

a = A()
b = A()
c = a * b  # inferred: Uninferable
