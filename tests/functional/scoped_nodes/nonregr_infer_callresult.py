class Delegate(object):
    def __get__(self, obj, cls):
        return getattr(obj._subject, self.attribute)

class CompositeBuilder(object):
    __call__ = Delegate()

builder = CompositeBuilder(result, composite)
tgts = builder()  # inferred: Uninferable
