import contextlib

class A:
    @contextlib.contextmanager
    def get(self):
        yield self

class B(A):
    def play():
        pass

with B().get() as b:
    b
b  # inferred: Instance(issue_1090_infer_yield_type_base_class.B)
