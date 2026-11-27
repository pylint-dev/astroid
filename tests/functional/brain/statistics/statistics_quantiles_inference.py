# Test that statistics.quantiles() returns Uninferable instead of empty list.
import statistics
statistics.quantiles(list(range(100)), n=4)  # inferred: Uninferable
