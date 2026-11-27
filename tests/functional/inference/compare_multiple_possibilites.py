from unknown import UNKNOWN
a = 1
if UNKNOWN:
    a = 2
b = 3
if UNKNOWN:
    b = 4
a < b  # inferred: Const(True)
