class MyClass:
    def __ge__(self, *args):
        return 'greater or equal'

MyClass().__ge__()  # inferred: Const('greater or equal')
