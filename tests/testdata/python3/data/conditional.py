from functools import partial

if False:
    def some_function(arg):
        pass

    def another_one(arg):
        pass
else:
    def some_function(arg):
        return 2

    another_one = partial(some_function, 1)
