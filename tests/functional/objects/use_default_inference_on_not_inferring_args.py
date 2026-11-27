class Test(object):
    def __init__(self):
        super(Lala, self)  # inferred: Instance(builtins.super)
        super(Test, lala)  # inferred: Instance(builtins.super)
