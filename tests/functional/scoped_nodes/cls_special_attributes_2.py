class A(object): pass  # getattr(__bases__): AssignAttr, Tuple(ClassDef(builtins.object))
class B(object): pass

A.__bases__ += (B,)
