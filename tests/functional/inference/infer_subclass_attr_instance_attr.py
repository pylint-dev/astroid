class Parent:
    def __init__(self):
        self.data = 123

class Test(Parent):
    pass
t = Test()
t.data  # inferred: Const(123)
