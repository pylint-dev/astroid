# Test len with objects that implement the len protocol
class A:
    def __len__(self):
        return 57
len(A())  # inferred: Const(57)
