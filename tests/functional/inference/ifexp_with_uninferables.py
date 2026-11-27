def truthy_and_falsy():
    return False if unknown() else True

def truthy_and_uninferable():
    return False if unknown() else unknown()

def calls_truthy_and_falsy():
    return 1 if truthy_and_falsy() else 2

def calls_truthy_and_uninferable():
    return 1 if range(10) else truthy_and_uninferable()

truthy_and_falsy()  # inferred: Const(False) | Const(True)
truthy_and_uninferable()  # inferred: Const(False) | Uninferable
calls_truthy_and_falsy()  # inferred: Const(1) | Const(2)
calls_truthy_and_uninferable()  # inferred: Const(1) | Const(False) | Uninferable
