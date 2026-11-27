class Outer:
    class Inner:
        data = 123
Inner = Outer.Inner

class Test(Inner):
    pass
Test.data  # inferred: Const(123)
