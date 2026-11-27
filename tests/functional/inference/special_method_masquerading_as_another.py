class Info(object):
    def __add__(self, other):
        return "lala"
    __or__ = __add__

f = Info()
f | Info()  # inferred: Const('lala')
