# Make sure proper len method is located
class F2(type):
    def __new__(cls, name, bases, attrs):
        return super().__new__(cls, name, bases, {})
    def __len__(self):
        return 57
class F(metaclass=F2):
    def __len__(self):
        return 4
len(F)  # inferred: Const(57)
len(F())  # inferred: Const(4)
