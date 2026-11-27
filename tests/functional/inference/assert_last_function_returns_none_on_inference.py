def check_equal(a, b):
    res = do_something_with_these(a, b)
    assert a == b == res

check_equal(a, b)  # inferred: Const(None)
