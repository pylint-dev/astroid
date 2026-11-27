# Test that other statistics functions are not affected by our brain module.
import statistics
# +2: <3.14: inferred: Instance(builtins.float) | Instance(builtins.int) | Uninferable
# +1: >=3.14: inferred: Instance(builtins.int) | Uninferable
statistics.mean([1, 2, 3, 4, 5])
