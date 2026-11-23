class A:
    def test(self): pass
a = A()
a.test.__func__  # inferred: FunctionDef(bound_method_model.A.test)
a.test.__self__  # inferred: Instance(bound_method_model.A)
