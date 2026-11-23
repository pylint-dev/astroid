from unknown import UNKNOWN
a = 1
if UNKNOWN:
    a = 3
b = 2
if UNKNOWN:
    b = 4
a < b  # inferred: Uninferable
