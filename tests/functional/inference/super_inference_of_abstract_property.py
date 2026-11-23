from abc import abstractmethod

class A:
   @property
   def test(self):
       return "super"

class C:
   @property
   @abstractmethod
   def test(self):
       "abstract method"

class B(A, C):

   @property
   def test(self):
        super()  # inferred: Super  # inferred.getattr(test): Const('super'), Uninferable
