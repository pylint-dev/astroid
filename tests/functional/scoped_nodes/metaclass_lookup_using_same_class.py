# Check that we don't have recursive attribute access for metaclass.
class A(object): pass  # getattr(mro): MroBoundMethod(builtins.type.mro)
