from unknown import Unknown
class A(object):
   def __add__(self, other): return NotImplemented
class B(object):
   def __add__(self, other): return Unknown
A() + Unknown  # inferred: Uninferable
Unknown + A()  # inferred: Uninferable
B() + A()  # inferred: Uninferable
A() + B()  # inferred: Uninferable
