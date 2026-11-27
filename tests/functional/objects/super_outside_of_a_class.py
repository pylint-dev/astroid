# A ``classmethod`` defined at module level does not crash inference.
#
# Regression test for https://github.com/pylint-dev/pylint/issues/8755
class C:
    pass

@classmethod
def foo(cls, a):
    b = super()  # value.inferred: Instance(builtins.super)
    return b.foo(a)

@classmethod
def bar(cls, a):
    b = super(C, cls)  # value.inferred: Super  # value.inferred.mro_pointer.name: 'C'
    return b.bar(a)
