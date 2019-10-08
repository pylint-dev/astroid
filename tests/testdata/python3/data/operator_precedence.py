assert not not True == True
assert (not False or True) == True
assert True or False and True
assert (True or False) and True

assert True is not (False is True) == False
assert True is (not False is True == False)

assert 1 + 2 + 3 == 6
assert 5 - 4 + 3 == 4
assert 4 - 5 - 6 == -7
assert 7 - (8 - 9) == 8
assert 2**3**4 == 2**81
assert (2**3)**4 == 8**4

assert 1 + 2 if (0.5 if True else 0.2) else 1 if True else 2 == 3
assert (0 if True else 1) if False else 2 == 2
assert lambda x: x if (0 if False else 0) else 0 if False else 0
assert (lambda x: x) if (0 if True else 0.2) else 1 if True else 2

assert ('1' + '2').replace('1', '3') == '32'
assert (lambda x: x)(1) == 1
assert ([0] + [1])[1] == 1
assert (lambda x: lambda: x + 1)(2)() == 3

f = lambda x, y, z: y(x, z)
assert f(1, lambda x, y: x + y[1], (2, 3)) == 4
