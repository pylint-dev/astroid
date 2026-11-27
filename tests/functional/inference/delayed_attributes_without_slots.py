class A(object):
    __slots__ = ('a', )
a = A()
a.teta = 24
a.a = 24
# +3: inferred: Instance(delayed_attributes_without_slots.A)
# +2: inferred.getattr(a): AssignAttr
# +1: inferred.getattr(teta): AttributeInferenceError
a
