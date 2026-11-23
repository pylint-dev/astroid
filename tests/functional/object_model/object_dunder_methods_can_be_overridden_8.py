class MyClass:
    def __str__(self, *args):
        return 'string repr'

MyClass().__str__()  # inferred: Const('string repr')
