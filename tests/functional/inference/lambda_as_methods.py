class X:
   m = lambda self, arg: self.z + arg
   z = 24

X().m(4)  # inferred: Const(28)
