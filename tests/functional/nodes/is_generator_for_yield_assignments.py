class A:
    def test(self):
        a = yield
        while True:
            print(a)
            yield a
a = A()
# +2: inferred: BoundMethod(is_generator_for_yield_assignments.A.test)
# +1: inferred.is_generator(): True
a.test
