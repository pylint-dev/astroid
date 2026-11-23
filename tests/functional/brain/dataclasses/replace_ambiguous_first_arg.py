# When the first arg has several possible types, replace yields Uninferable.
import dataclasses
from dataclasses import dataclass

@dataclass
class A:
    x: int = 0

@dataclass
class B:
    x: int = 0

def f(cond):
    obj = A() if cond else B()
    dataclasses.replace(obj, x=1)  # inferred: Uninferable
