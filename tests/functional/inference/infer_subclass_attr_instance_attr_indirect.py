class Parent:
    def __init__(self):
        self.data = 123

class Test(Parent):
    pass
t = Test()
# +2: inferred: Instance(infer_subclass_attr_instance_attr_indirect.Test)
# +1: inferred.igetattr(data): Const(123)
t
