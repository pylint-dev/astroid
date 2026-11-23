# Inferring such an argument yields ``Uninferable`` rather than crashing.
def f(x, *y, y: tuple[x]): ...  # args.kwonlyargs_annotations[0].slice.inferred: Uninferable
