class A:
    method = lambda self, b, /, c: b + c

    def __init__(self, other=(), /, **kw):
        self  # inferred: Instance(posonlyargs_inference.A)
A()  # inferred: Instance(posonlyargs_inference.A)
A().method  # inferred: BoundMethod(posonlyargs_inference.A.<lambda>)  # inferred.type: 'method'
