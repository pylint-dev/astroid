# Test constraint for equality of callables.
class Foo:
    pass

def bar():
    pass

baz = lambda i : i

x, y, z = Foo, bar, baz

if x == Foo:
    x  # inferred: ClassDef(equality_callable.Foo)
if x != Foo:
    x  # inferred: Uninferable

if y == bar:
    y  # inferred: FunctionDef(equality_callable.bar)
if y != bar:
    y  # inferred: Uninferable

if z == baz:
    z  # inferred: Lambda(equality_callable.<lambda>)
if z != baz:
    z  # inferred: Uninferable
