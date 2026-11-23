class Index(object):
    def __index__(self): return 2
class NotIndex(object): pass
class NotIndex2(object):
    def __index__(self): return None
a = [1, 2]
# +2: inferred: List([1, 2, 1, 2])
# +1: inferred.itered(): [Const(1), Const(2), Const(1), Const(2)]
a * Index()
a * NotIndex()  # inferred: Uninferable
a * NotIndex2()  # inferred: Uninferable
