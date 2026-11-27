class A:
    pass
class B:
    pass
class Scope:
    pass
scope = Scope()
scope.A = A
scope.B = B
# +1: mro: mro_with_attribute_classes.C, mro_with_attribute_classes.A, mro_with_attribute_classes.B, builtins.object
class C(scope.A, scope.B):
    pass
