def test(a, **kwargs): return a
test(*missing)  # inferred: Uninferable
test(*object)  # inferred: Uninferable
test(*1)  # inferred: Uninferable


def test(**kwargs): return kwargs
test(**miss)  # inferred: Uninferable
test(**(1, 2))  # inferred: Uninferable
test(**1)  # inferred: Uninferable
test(**{misss:1})  # inferred: Uninferable
test(**{object:1})  # inferred: Uninferable
test(**{1:1})  # inferred: Uninferable
test(**{'a':1, 'a':1})  # inferred: Uninferable

def test(a): return a
test()  # inferred: Uninferable
test(1, 2, 3)  # inferred: Uninferable

from unknown import unknown
test(*unknown)  # inferred: Uninferable
def test(*args): return args
test(*unknown)  # inferred: Uninferable
