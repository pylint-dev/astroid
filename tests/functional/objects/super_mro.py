class A(object): pass
class B(A): pass
class C(A): pass
class E(C, B):
    def __init__(self):
        super(E, self)  # inferred: Super  # inferred.mro: -
        super(C, self)  # inferred: Super  # inferred.mro: -
        super(B, self)  # inferred: Super  # inferred.mro: -

        super(B, 1)  # inferred: Super  # inferred.super_mro(): SuperError
        super(1, B)  # inferred: Super  # inferred.super_mro(): SuperError
