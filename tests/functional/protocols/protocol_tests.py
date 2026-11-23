# list multiplication with empty list and overflowing multiplier
[] * 1163845194457646539560  # inferred: List([])
# list multiplication with zero multiplier
[0] * 0  # inferred: List([])
# list multiplication with negative overflowing multiplier
[0] * -9223372036854775809  # inferred: List([])
