class Pouet:
    __name__ = "pouet"
# +2: inferred: Instance(explicit___name__.Pouet)
# +1: inferred.getattr(__name__): AssignName(__name__)
p1 = Pouet()

class PouetPouet(Pouet): pass
# +2: inferred: Instance(explicit___name__.Pouet)
# +1: inferred.getattr(__name__): AssignName(__name__)
p2 = Pouet()

class NoName: pass  # getattr(__name__): Const('NoName')
# +2: inferred: Instance(explicit___name__.NoName)
# +1: inferred.getattr(__name__): AttributeInferenceError
p3 = NoName()
