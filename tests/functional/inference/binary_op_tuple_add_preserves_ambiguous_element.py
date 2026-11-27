def choose():
    value = 1
    if value < 0:
        value = -value
    return value

# +1: inferred: Tuple(Const(0), Unknown(Unknown.Unknown()), Const(2))
(0, choose()) + (2,)
