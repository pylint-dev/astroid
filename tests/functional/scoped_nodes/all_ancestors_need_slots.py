class A(object):
    __slots__ = ('a', )
class B(A): pass  # slots: None
class C(B):  # slots: None
    __slots__ = ('a', )
