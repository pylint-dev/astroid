def truth_branch():
    return 1 if True else 2

def false_branch():
    return 1 if False else 2

def both_branches():
    return 1 if unknown() else 2

truth_branch()  # inferred: Const(1)
false_branch()  # inferred: Const(2)
both_branches()  # inferred: Const(1) | Const(2)
