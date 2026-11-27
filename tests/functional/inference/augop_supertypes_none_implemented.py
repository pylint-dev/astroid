class A(object): pass
class B(object): pass
a = A()
a += B()  # inferred: Uninferable
