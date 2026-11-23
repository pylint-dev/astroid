# The concatenated list would be prohibitively expensive to build.
([1] * 50000001) + ([1] * 50000001)  # inferred: Uninferable
