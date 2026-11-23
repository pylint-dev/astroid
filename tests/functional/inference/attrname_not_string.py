getattr(1, 1)  # inferred: InferenceError
c = int
getattr(1, c)  # inferred: InferenceError
