import abc

class A(object):
    @abc.abstractproperty
    def test(self):
        return 42

a = A()
x = a.test  # inferred: Const(42)
