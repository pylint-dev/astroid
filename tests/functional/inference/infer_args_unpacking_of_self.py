class A:
    def __init__(*args, **kwargs):
        self, *args = args
        self.data = {1: 2}
        self  # inferred: Instance(infer_args_unpacking_of_self.A)
A().data  # inferred: Dict({1: 2})
