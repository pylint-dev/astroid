class Outer:
    data = 123

class Test(Outer):
    pass
Test.data  # inferred: Const(123)
