class A(object):
    def __init__(self): pass
class B(A):
    def __init__(self, arg, arg2): pass
# +2: local_attr('__init__')[0]: FunctionDef(local_attr_mro.A.__init__)
# +1: local_attr('__init__')[0].parent.name: 'A'
class C(A): pass
# +3: local_attr('__init__')[0]: FunctionDef(local_attr_mro.B.__init__)
# +2: local_attr('__init__')[0].parent.name: 'B'
# +1: local_attr_ancestors('__init__'): ClassDef(local_attr_mro.B) | ClassDef(local_attr_mro.A) | ClassDef(builtins.object)
class D(C, B): pass
