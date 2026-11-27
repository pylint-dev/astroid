def func(elems):
    return elems

class BaseModel(object):

    def __init__(self, *args, **kwargs):
        self._reference = func(*self._reference.split('.'))
BaseModel()._reference  # inferred: Uninferable
