from unknown import unknown

def test(a):
   return a + 1

def func():
    a = {unknown: 'a'}
    return {0: 1, **a}

test(**func())  # inferred: Uninferable
