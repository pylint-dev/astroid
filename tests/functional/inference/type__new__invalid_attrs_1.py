type.__new__(type, 'a', (), ())  # inferred: InferenceError
type.__new__(type, 'a', (), object)  # inferred: InferenceError
type.__new__(type, 'a', (), 1)  # inferred: InferenceError
