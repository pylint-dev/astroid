def test(f):
     return f
test(f=23, **{'f': 34})  # inferred: Uninferable
def test(f=None):
     return f
test(f=23, **{'f':23})  # inferred: Uninferable
