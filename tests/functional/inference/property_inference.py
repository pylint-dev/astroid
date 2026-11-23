class A:
    @property
    def test(self):
        return 42

    @test.setter
    def test(self, value):
        return "banco"

# +2: inferred: Property(property_inference.A.test) | UnboundMethod(property_inference.A.test)
# +1: inferred.type: 'method' | 'property'
A.test
A().test  # inferred: BoundMethod(property_inference.A.test) | Const(42)
A.test.fget(A)  # inferred: Const(42)
A.test.fset(A, "a_value")  # inferred: Const('banco')
A.test.setter  # inferred: FunctionDef(property_inference.A.test.setter)
A.test.getter  # inferred: FunctionDef(property_inference.A.test.getter)
A.test.deleter  # inferred: FunctionDef(property_inference.A.test.deleter)
