def with_default(foo: str | None = None):
    a = 1 if foo else "bar"  # value.inferred: Const('bar') | Const(1)

def without_default(foo: str):
    a = 1 if foo else "bar"  # value.inferred: Const('bar') | Const(1)

def some_ifexps(foo: str | None = None):
    a = 1 if foo else 2
    b = 3 if a else 4  # value.inferred: Const(3)
    c = 4 if b else 5  # value.inferred: Const(4)
    d = 5 if not foo else foo  # value.inferred: Const(5) | Uninferable
    e = d if not foo else foo  # value.inferred: Const(5) | Uninferable | Uninferable
