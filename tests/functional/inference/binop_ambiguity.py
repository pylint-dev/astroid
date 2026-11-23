class A(object):
   def __add__(self, other):
       if isinstance(other, B):
            return NotImplemented
       if type(other) is type(self):
            return 42
       return NotImplemented
class B(A): pass
class C(object):
   def __radd__(self, other):
       if isinstance(other, B):
           return 42
       return NotImplemented
A() + B()  # inferred: Uninferable
B() + A()  # inferred: Uninferable
A() + C()  # inferred: Uninferable
C() + A()  # inferred: Uninferable
