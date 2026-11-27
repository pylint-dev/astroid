class X(object):
    M = lambda self, arg: arg + 1
    x = 24
    def __init__(self):
        y = self
        self.m = y.M(1) + y.z

class C(object):
    z = 24

class Y(X, C):
    M = lambda self, arg: arg + 1
    def blurb(self):
        self.m  # inferred: Const(26)
