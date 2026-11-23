def _bind(arg):
    return arg.bind

class A(object):
    @property
    def bind(self):
        return 42
    def irrelevant(self):
        # This is important, because it used to trigger
        # a maximum recursion error.
        bind = _bind(self)
        return bind
# +4: inferred: Instance(extra_decorators_only_class_level_assignments.A)
# +3: inferred.igetattr(bind): Const(42)
# +2: inferred.igetattr(bind).scope().extra_decorators: []
# +1: inferred.igetattr(bind).value: 42
A()
