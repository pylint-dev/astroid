# Check if we added discard nodes as yield parent (w/ compiler).
# +4: body[0]: Expr(yield 0)
# +3: body[0].value: Yield(yield 0)
# +2: body[1].body[0]: Expr(yield more)
# +1: body[1].body[0].value: Yield(yield more)
def yiell():
    yield 0
    if no:
        yield more
