type.__new__(type, 'foo')  # inferred: InferenceError
type.__new__(type, 'foo', ())  # inferred: InferenceError
type.__new__(type, 'foo', (), {}, ())  # inferred: InferenceError
