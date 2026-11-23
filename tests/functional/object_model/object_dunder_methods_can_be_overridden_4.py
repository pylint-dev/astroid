class MyClass:
    def __lt__(self, *args):
        return 'less than'

MyClass().__lt__()  # inferred: Const('less than')
