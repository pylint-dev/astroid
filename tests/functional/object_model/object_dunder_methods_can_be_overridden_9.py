class MyClass:
    def __repr__(self, *args):
        return 'repr'

MyClass().__repr__()  # inferred: Const('repr')
