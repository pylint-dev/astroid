from random import sample
class A: pass
sample(list({1: A()}.values()), 1)  # inferred: List(Call(A()))
