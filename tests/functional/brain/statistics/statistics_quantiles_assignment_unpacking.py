# Test the specific case that was causing false positives.
import statistics
q1, q2, q3 = statistics.quantiles(list(range(100)), n=4)  # value.inferred: Uninferable
