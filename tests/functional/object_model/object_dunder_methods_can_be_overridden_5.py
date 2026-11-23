class MyClass:
    def __le__(self, *args):
        return 'less or equal'

MyClass().__le__()  # inferred: Const('less or equal')
