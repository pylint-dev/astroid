class C:
    def test(self): pass
    @staticmethod
    def static(): pass
    @classmethod
    def class_method(cls): pass
    def __call__(self): pass
class D(C):
    pass
class NotReallyCallableDueToPythonMisfeature(object):
    __call__ = 42
callable(C.test)  # inferred: Const(True)
callable(C.static)  # inferred: Const(True)
callable(C.class_method)  # inferred: Const(True)
callable(C().test)  # inferred: Const(True)
callable(C().static)  # inferred: Const(True)
callable(C().class_method)  # inferred: Const(True)
C  # inferred: ClassDef(callable_methods.C)
C()  # inferred: Instance(callable_methods.C)
# +1: inferred: Instance(callable_methods.NotReallyCallableDueToPythonMisfeature)
NotReallyCallableDueToPythonMisfeature()
staticmethod  # inferred: ClassDef(builtins.staticmethod)
classmethod  # inferred: ClassDef(builtins.classmethod)
property  # inferred: ClassDef(builtins.property)
D  # inferred: ClassDef(callable_methods.D)
D()  # inferred: Instance(callable_methods.D)
