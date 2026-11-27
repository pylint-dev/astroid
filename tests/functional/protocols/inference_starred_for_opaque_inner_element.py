# Inferring the starred name itself must not raise ``TypeError``.
for a, (b, *c) in [[1, object()]]:
    c  # inferred: Uninferable
