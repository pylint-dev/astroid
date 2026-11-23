class MyClass:
    def __gt__(self, *args):
        return 'greater than'

MyClass().__gt__()  # inferred: Const('greater than')
