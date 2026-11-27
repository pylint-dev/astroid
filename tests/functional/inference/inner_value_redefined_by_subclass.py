class X(object):
    M = lambda self, arg: "a"
    x = 24
    def __init__(self):
        x = 24
        self.m = self.M(x)

class Y(X):
    M = lambda self, arg: arg + 1
    def blurb(self):
        self.m  # inferred: Const(25)
