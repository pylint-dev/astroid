class A:
    def b(self):
        return 0

    @classmethod
    def c(cls):
        return cls(), 0

class D:
    def e(self):
        self.f = A.c()[0]
        # +1: inferred: Instance(classmethod_returned_tuple_subscript_ignores_unrelated_boundnode.A)
        self.f
