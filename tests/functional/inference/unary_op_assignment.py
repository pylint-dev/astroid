class A(object): pass
def pos(self):
    return 42
A.__pos__ = pos
f = A()
+f  # inferred: Const(42)
