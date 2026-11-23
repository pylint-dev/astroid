next = 42
def wrapper(next=next):
     next = 24
     def test():
         return next
     return test
wrapper()()  # inferred: Const(24)
