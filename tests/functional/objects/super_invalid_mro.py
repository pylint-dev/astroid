class A(object):
   test = 42
class Super(A, A):
   def __init__(self):
       super(Super, self)  # inferred: Super  # inferred.getattr(test): AttributeInferenceError
