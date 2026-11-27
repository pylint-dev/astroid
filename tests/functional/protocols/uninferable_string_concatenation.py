# The concatenated string would be prohibitively expensive to build.
("a" * 60000000) + ("b" * 60000000)  # inferred: Uninferable
