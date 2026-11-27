class NoGetitem(object):
    pass
class InvalidGetitem(object):
    def __getitem__(self): pass
class InvalidGetitem2(object):
    __getitem__ = 42
NoGetitem()[4]  # inferred: InferenceError
InvalidGetitem()[5]  # inferred: InferenceError
InvalidGetitem2()[10]  # inferred: InferenceError
[1, 2, 3][None]  # inferred: InferenceError
'lala'['bala']  # inferred: InferenceError
