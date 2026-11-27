# If 'self' is referenced within a list it should not be bound by it.
#
# Reported in https://github.com/pylint-dev/pylint/issues/4826.
class A:
    def __init__(self):
        for a in [self] + []:
            # +2: args[0].inferred: Instance(binop_self_in_list.A)
            # +1: args[0].inferred._proxied.name: 'A'
            print(a)

class B:
    def __init__(self):
        for b in [] + [self]:
            # +2: args[0].inferred: Instance(binop_self_in_list.B)
            # +1: args[0].inferred._proxied.name: 'B'
            print(b)
