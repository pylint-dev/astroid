def f():
    print('non-empty, non-pass, no return statements')
value = f()
value  # inferred: Const(None)
