# ``__new__`` is a static method: the class is passed explicitly.
#
# Regression test for https://github.com/pylint-dev/pylint/issues/8325
class A:
    def clone(self):
        return self.__new__(type(self))

a = A()
# +5: inferred: BoundMethod(builtins.object.__new__)
# +4: inferred.argnames(): cls, args, kwargs
# +3: inferred.args.kwarg: 'kwargs'
# +2: inferred.args.vararg: 'args'
# +1: inferred.implicit_parameters(): 0
a.__new__
a.clone()  # inferred: Instance(instance_dunder_new_accepts_explicit_class.A)
