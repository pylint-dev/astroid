class A(object):
    def first(self, arg1, arg2):
        return arg1
    @classmethod
    def method(cls, arg1, arg2):
        return arg2
    @classmethod
    def empty(cls):
        return 2
    @staticmethod
    def static(arg1, arg2):
        return arg1
    def empty_method(self):
        return []
x = A().first(1, [])  # inferred: Const(1)
y = A.method(1, [])  # inferred: List([])
z = A.static(1, [])  # inferred: Const(1)
empty = A.empty()  # inferred: Const(2)
empty_list = A().empty_method()  # inferred: List([])
