try:
    1/0
except ValueError:
    name = 1
try:
    1/0
except OSError:
    name = 2
    name  # inferred: Const(2)
