class DummyContext(object):
    def __enter__(self):
        return self
    def __exit__(self, ex_type, ex_value, ex_tb):
        return True

if False:
    with DummyContext() as con:
        pass

with DummyContext() as con:
    # +1: inferred: BoundMethod(prevent_recursion_error_in_igetattr_and_context_manager_inference.DummyContext.__enter__)
    con.__enter__
