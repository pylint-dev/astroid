# Test that a condition matching no supported constraint doesn't filter.
[L for L in [[1, 2], [3, 4]] if sum(L) == 3]  # elt.inferred: List([1, 2]) | List([3, 4])
