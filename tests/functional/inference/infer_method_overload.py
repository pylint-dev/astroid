class A:
    def foo(self): ...

    def foo(self):
        yield

A().foo()  # inferred: Generator(builtins.generator)
