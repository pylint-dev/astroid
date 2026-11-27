class FirstParent(object):
    __slots__ = ('a', 'b', 'c')
class SecondParent(FirstParent):
    __slots__ = ('d', 'e')
class Third(SecondParent):  # slots: a, b, c, d, d, e
    __slots__ = ('d', )
