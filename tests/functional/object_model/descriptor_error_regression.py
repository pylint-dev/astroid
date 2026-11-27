# Make sure the following code does node cause an exception.
class MyClass:
    text = "MyText"

    def mymethod1(self):
        return self.text

    def mymethod2(self):
        return self.mymethod1.__get__(self, MyClass)


cl = MyClass().mymethod2()()
cl  # inferred: Const('MyText')
