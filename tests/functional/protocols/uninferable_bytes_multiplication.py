# Building the repeated bytes would be prohibitively expensive.
b"abc" * 123456789  # inferred: Uninferable
