from unknown import Unknown
for a, *b in something:
    b  # inferred: Uninferable
for a, *b in Unknown:
    b  # inferred: Uninferable
for a, *b in (1):
    b  # inferred: Uninferable
