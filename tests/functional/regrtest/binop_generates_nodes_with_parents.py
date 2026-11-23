def no_op(*args):
    pass
def foo(*args):
    def inner(*more_args):
        args + more_args  # inferred: Tuple(())  # inferred.parent: BinOp(args + more_args)
    return inner
