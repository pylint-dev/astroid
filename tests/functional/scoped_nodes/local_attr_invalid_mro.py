# A has an invalid MRO, local_attr should fallback
# to using .ancestors.
class A(object, object):
    test = 42
class B(A):  # local_attr('test')[0].inferred: Const(42)
    pass
