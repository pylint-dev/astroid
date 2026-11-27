class A(type):
    @classmethod
    def test(cls, first): return first
    def __new__(cls, name, bases, dictionary):
        return super().__new__(cls, name, bases, dictionary)

# +2: inferred: BoundMethod(implicit_parameters_bound_method.A.test)
# +1: inferred.implicit_parameters(): 1
A.test
# +2: inferred: BoundMethod(implicit_parameters_bound_method.A.__new__)
# +1: inferred.implicit_parameters(): 0
A.__new__
