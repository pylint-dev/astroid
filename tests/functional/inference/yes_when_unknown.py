from unknown import unknown, any, not_any
0 and unknown  # inferred: Uninferable
unknown or 0  # inferred: Uninferable
any or not_any and unknown  # inferred: Uninferable
