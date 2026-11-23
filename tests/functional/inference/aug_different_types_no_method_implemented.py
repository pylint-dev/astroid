class A(object): pass
class B(object): pass
f = A()
f += B()  # inferred: Uninferable
