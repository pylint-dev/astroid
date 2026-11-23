from collections import Missing
class A(object):
    def __init__(self):
        super(Missing, self)  # inferred: Instance(builtins.super)
        super(A, Missing)  # inferred: Instance(builtins.super)
