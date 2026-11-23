from functools import partial

def test(x):
    return x

p = partial(test, x=1)
a = p.__get__({})
# +2: inferred: BoundMethod(PartialFunction)
# +1: inferred._proxied._proxied: PartialFunction(PartialFunction)
a
a()  # inferred: Const(1)  # inferred._proxied._proxied: AttributeError
