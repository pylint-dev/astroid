class Parent(object):
    @property
    def foo(self):
        pass

class Child(Parent):
    @Parent.foo.getter
    def foo(self):
    # -1: inferred: FunctionDef(decorator_names_inference_error_leaking.Child.foo)
    # -2: inferred.decoratornames(): {'decorator_names_inference_error_leaking.Parent.foo.getter'}
        return super(Child, self).foo + ['oink']
