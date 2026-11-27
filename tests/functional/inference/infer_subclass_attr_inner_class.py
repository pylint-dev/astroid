class Outer:
    class Inner:
        data = 123

class Test(Outer.Inner):
    pass
# +2: inferred: ClassDef(infer_subclass_attr_inner_class.Test)
# +1: inferred.igetattr(data): Const(123)
Test
Test.data  # inferred: Const(123)
