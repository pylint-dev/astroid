class Module(object):
    pass
class StaticMethod(object):
    @staticmethod
    def static():
        # valid, but we don't bother with it.
        return super(StaticMethod, StaticMethod)  # value.inferred: Instance(builtins.super)
# super outside methods aren't inferred
super(Module, Module)  # inferred: Instance(builtins.super)
# no argument super is not recognised outside methods as well.
super()  # inferred: Instance(builtins.super)
