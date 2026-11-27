x = [A] * 1
f = [x, [A] * 2]
x = list(f) + [] # List[Uninferable]
tuple(x[0])  # inferred: Tuple(())
