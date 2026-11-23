def func(a):  # inferred: FunctionDef(compare_unknown.func)
    if tuple() + (a[1],) in set():
        raise Exception()
