class MyClass:
    def __ne__(self, *args):
        return 'not equal'

MyClass().__ne__()  # inferred: Const('not equal')
