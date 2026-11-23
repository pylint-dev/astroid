class custom_property(property):
    pass

class MyClass(object):
    @custom_property
    def my_prop(self):
        return 1

MyClass().my_prop  # inferred: Const(1)
