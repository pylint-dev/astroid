def choice(flag):
    if flag:
        return 1
    return 2
values = [0]
values += (choice(True), 3)
# +1: inferred: List(Const(0), Unknown(Unknown.Unknown()), Const(3))
values
